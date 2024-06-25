#! /usr/bin/env python3

import argparse
import concurrent.futures
import itertools
import logging
import os
import pathlib
import signal
import sys
import textwrap
import time
from datetime import datetime

from senzing import (
    SzConfigManager,
    SzDiagnostic,
    SzEngine,
    SzEngineFlags,
    SzError,
    SzProduct,
)

try:
    import orjson as json
except ModuleNotFoundError:
    import json

# TODO
__version__ = "1.3.0"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = "2022-11-29"
__updated__ = "2023-12-19"


# Custom actions for argparse. Enables checking if an arg "was specified" on the CLI to check if CLI args should take
# precedence over env vars and still can use the default setting for an arg if neither were specified.
class CustomArgActionStoreTrue(argparse.Action):
    """Set to true like using normal action=store_true and set _specified key for lookup"""

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, True)
        setattr(namespace, self.dest + "_specified", True)


class CustomArgAction(argparse.Action):
    """Set to value and set _specified key for lookup"""

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        setattr(namespace, self.dest + "_specified", True)


def arg_convert_boolean(env_var, cli_arg):
    """Convert boolean env var to True or False if set, otherwise use cli arg value"""
    evar = os.getenv(env_var)
    if evar:
        if isinstance(evar, str):
            if evar.lower() in ["true", "1", "t", "y", "yes"]:
                return True
            return False
        return evar
    return cli_arg


def startup_info(engine, diag, configmgr, product):
    """Fetch and display information at startup."""

    try:
        lic_info = json.loads(product.get_license())
        ver_info = json.loads(product.get_version())
        response = configmgr.get_configs()
        config_list = json.loads(response)
        active_cfg_id = engine.get_active_config_id()
        ds_info = json.loads(diag.get_datastore_info())
    except SzError as ex:
        logger.error(f"Failed to get startup information: {ex}")
        sys.exit(-1)

    # Get details for the currently active config ID
    active_cfg_details = [
        details
        for details in config_list["CONFIGS"]
        if details["CONFIG_ID"] == active_cfg_id
    ]
    config_comments = active_cfg_details[0]["CONFIG_COMMENTS"]
    config_created = active_cfg_details[0]["SYS_CREATE_DT"]

    # Get data store info, build list of strings, could be a cluster
    ds_list = []
    for ds in ds_info["dataStores"]:
        ds_list.append(f"{ds['id']} - {ds['type']} - {ds['location']}")

    logger.info("")
    logger.info("Version & Configuration")
    logger.info("-----------------------")
    logger.info("")
    logger.info(
        "Senzing Version:           "
        f" {ver_info['VERSION'] + ' (' + ver_info['BUILD_DATE'] + ')'  if 'VERSION' in ver_info else ''}"
    )
    logger.info(f"Instance Config ID:         {active_cfg_id}")
    logger.info(f"Instance Config Comments:   {config_comments}")
    logger.info(f"Instance Config Created:    {config_created}")
    logger.info(f"Datastore(s):               {ds_list.pop(0)}")
    for ds in ds_list:
        logger.info(f"{' ' * 28}{ds}")
    logger.info("")
    logger.info("License")
    logger.info("-------")
    logger.info("")
    logger.info(f'Customer:    {lic_info["customer"]}')
    logger.info(f'Type:        {lic_info["licenseType"]}')
    logger.info(f'Records:     {lic_info["recordLimit"]}')
    logger.info(f'Expiration:  {lic_info["expireDate"]}')
    logger.info(f'Contract:    {lic_info["contract"]}')
    logger.info("")


def add_record(engine, rec_to_add, with_info):
    """Add a single record, returning with info details if --info or SENZING_WITHINFO was specified"""
    record_dict = json.loads(rec_to_add)
    data_source = record_dict.get("DATA_SOURCE", None)
    record_id = record_dict.get("RECORD_ID", None)

    if with_info:
        response = engine.add_record(
            data_source, record_id, rec_to_add, SzEngineFlags.SZ_WITH_INFO
        )
        return response

    engine.add_record(data_source, record_id, rec_to_add)
    return None


def get_redo_record(engine):
    """Get a redo record for processing"""
    try:
        redo_record = engine.get_redo_record()
    except SzError as ex:
        logger.critical(f"Exception: {ex} - Operation: getRedoRecord")
        global do_shutdown
        do_shutdown = True
        # TODO For typing this would be ""
        return None

    return redo_record


def prime_redo_records(engine, quantity):
    """Get a specified number of redo records for priming processing"""
    redo_records = []
    for _ in range(quantity):
        single_redo_rec = get_redo_record(engine)
        if single_redo_rec:
            redo_records.append(single_redo_rec)
    return redo_records


def process_redo_record(engine, record, with_info):
    """Process a single redo record, returning with info details if --info or SENZING_WITHINFO was specified"""
    if with_info:
        response = engine.process_redo_record(record, SzEngineFlags.SZ_WITH_INFO)
        return response

    engine.process_redo_record(record)
    return None


def record_stats(success_recs, error_recs, prev_time, operation):
    """Log details on records for add/redo"""
    logger.info(
        f"Processed {success_recs:,} {operation},"
        f" {int(1000 / (time.time() - prev_time)):,} records per second,"
        f" {error_recs} errors"
    )
    return time.time()


def workload_stats(engine):
    """Log engine workload stats"""
    try:
        stats = engine.get_stats()
        logger.info("")
        logger.info(stats)
        logger.info("")
    except SzError as ex:
        logger.critical(f"Exception: {ex} - Operation: get_stats")
        global do_shutdown
        do_shutdown = True


def long_running_check(futures, time_now, num_workers):
    """Check for long-running records"""
    num_stuck = 0
    for fut, payload in futures.items():
        if not fut.done():
            duration = time_now - payload[PAYLOAD_START_TIME]
            if duration > LONG_RECORD:
                num_stuck += 1
                stuck_record = json.loads(payload[PAYLOAD_RECORD])
                logger.warning(
                    f"Long running record ({duration / 60:.3g}):"
                    f" {stuck_record['DATA_SOURCE']} - {stuck_record['RECORD_ID']}"
                )

    if num_stuck >= num_workers:
        logger.warning(
            f"All {num_workers} threads are stuck processing long running records"
        )


def signal_int(signum, frame):
    """Interrupt to allow running threads to finish"""
    logger.warning(
        "Please wait for running tasks to complete, this could take many minutes...\n"
    )
    global do_shutdown
    do_shutdown = True


def load_and_redo(
    engine,
    file_input,
    file_output,
    file_errors,
    num_workers,
    no_redo,
    with_info,
):
    """Load records and process redo records after loading is complete"""

    def add_new_future():
        """Add a new feature as needed"""
        if mode.__name__ == "add_record":
            record = in_file.readline()
        else:
            record = get_redo_record(engine)

        if record:
            futures[
                executor.submit(
                    mode,
                    engine,
                    record,
                    with_info,
                )
            ] = (record, time.time())
            return False
        else:
            return True

    global do_shutdown
    load_errors = load_success = redo_errors = redo_success = redo_time = 0

    mode_text = {
        "add_record": {
            "start_msg": "Starting to load with",
            "except_msg": "add_record",
            "results_header": "Loading",
            "results_rec_type": "load",
            "stats_msg": "adds",
        },
        "process_redo_record": {
            "start_msg": "Starting to process redo records with",
            "except_msg": "process_redo_record",
            "results_header": "Redo",
            "results_rec_type": "redo",
            "stats_msg": "redos",
        },
    }

    # Test the max number of workers ThreadPoolExecutor allocates to use in sizing actual workers to request
    with concurrent.futures.ThreadPoolExecutor() as test:
        test_workers = test._max_workers
    max_workers = num_workers if num_workers else test_workers

    if ingest_file:
        in_file = open(file_input, "r")

    modes = [add_record] if no_redo else [add_record, process_redo_record]
    main_start_time = time.time()

    with open(file_output, "w") as out_file:
        for mode in modes:
            # If loading is stopped or fails don't process redo
            if do_shutdown:
                break

            add_future = True
            end_of_recs = False
            success_recs = error_recs = 0

            # If the file was empty or no file was specified skip loading
            if mode.__name__ == "add_record" and not ingest_file:
                logger.info("")
                logger.info(
                    "No input file. Skipping loading, checking for redo records..."
                )
                load_time = 0
                continue

            start_time = long_check_time = work_stats_time = prev_time = time.time()

            with concurrent.futures.ThreadPoolExecutor(max_workers) as executor:
                if mode.__name__ == "add_record":
                    futures = {
                        executor.submit(mode, engine, record, with_info): (
                            record,
                            time.time(),
                        )
                        for record in itertools.islice(in_file, executor._max_workers)
                    }
                else:
                    futures = {
                        executor.submit(mode, engine, record, with_info): (
                            record,
                            time.time(),
                        )
                        for record in prime_redo_records(engine, executor._max_workers)
                    }
                logger.info("")
                logger.info(
                    f"{mode_text[mode.__name__]['start_msg']} {executor._max_workers} threads..."
                )
                logger.info("")

                while futures:
                    done, _ = concurrent.futures.wait(
                        futures, return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    for f in done:
                        try:
                            result = f.result()
                        except (
                            SzBadInputError,
                            SzRetryableError,
                            json.JSONDecodeError,
                        ) as ex:
                            logger.error(
                                f"Exception: {ex} - Operation:"
                                f" {mode_text[mode.__name__]['except_msg']} -"
                                f" Record: {futures[f][PAYLOAD_RECORD]}"
                            )
                            error_recs += 1
                        except SzError as ex:
                            logger.critical(
                                f"Exception: {ex} - Operation:"
                                f" {mode_text[mode.__name__]['except_msg']} -"
                                f" Record: {futures[f][PAYLOAD_RECORD]}"
                            )
                            error_recs += 1
                            do_shutdown = True
                        else:
                            if add_future and not do_shutdown:
                                end_of_recs = add_new_future()

                            if result:
                                out_file.write(result + "\n")

                            success_recs += 1
                            if success_recs % 1000 == 0:
                                prev_time = record_stats(
                                    success_recs,
                                    error_recs,
                                    prev_time,
                                    mode_text[mode.__name__]["stats_msg"],
                                )
                        finally:
                            del futures[f]

                    # # TODO Keep?
                    # Early errors check to catch mis-mapping, missing dsrc_code, etc
                    if error_recs == executor._max_workers:
                        logger.info("")
                        # TODO Does this show the errors file?
                        logger.error(
                            f"All initial {executor._max_workers:,} records failed! Stopping processing, please review the errors file."
                        )
                        logger.info("")
                        do_shutdown = True
                    # if success_recs <= 100 and error_recs > 50:
                    #     logger.critical(
                    #         f"Shutting down - {success_recs = } - {error_recs = }"
                    #     )
                    #     print(f"{len(futures) = }")
                    #     do_shutdown = True

                    if (do_shutdown or end_of_recs) and len(futures) == 0:
                        break

                    time_now = time.time()
                    if time_now > work_stats_time + WORK_STATS_INTERVAL:
                        work_stats_time = time_now
                        workload_stats(engine)

                    if time_now > long_check_time + LONG_RECORD:
                        long_check_time = time_now
                        long_running_check(futures, time_now, executor._max_workers)

            if not do_shutdown:
                workload_stats(engine)

            if do_shutdown:
                logger.warning("Processing was interrupted, shutting down.")
                logger.info("")

            # TODO Add same for redo so don't get 100 error on redo when first 100 load fail
            # Store loading stats for overall results stats
            if mode.__name__ == "add_record":
                load_time = round((time.time() - main_start_time) / 60, 1)
                load_errors = error_recs
                load_success = success_recs
                if not do_shutdown:
                    logger.info(
                        f"Successfully loaded {load_success:,} records in"
                        f" {load_time} mins with"
                        f" {load_errors:,} error(s)"
                    )
            else:
                redo_time = 0 if no_redo else round((time.time() - start_time) / 60, 1)
                redo_errors = error_recs
                redo_success = success_recs

        if no_redo:
            logger.info("")
        logger.info("Results")
        logger.info("-------")
        logger.info("")
        logger.info(
            # TODO Make files Path objects earlier
            "Source file:                "
            f"{pathlib.Path(file_input).resolve() if file_input else 'No input file specified'}"
        )
        logger.info(
            "With info file:             "
            f"{pathlib.Path(file_output).resolve() if with_info else 'With info responses not requested'}"
        )
        logger.info(
            "Errors file                 "
            f"{pathlib.Path(errors_file).resolve() if (load_errors + error_recs) > 0 else 'No errors'}"
        )
        logger.info("")
        # TODO Language?
        logger.info(f"Successful loaded records:  {load_success:,}")
        logger.info(f"Error loaded records:       {load_errors:,}")
        logger.info(f"Loading elapsed time (s):   {load_time}")
        logger.info("")
        logger.info(
            # f"Successful redo records:    {f'{redo_success:,}' if not no_redo else no_redo_msg}"
            f"Successful redo records:    {f'{redo_success:,}' if not no_redo else 'Redo disabled'}"
        )
        logger.info(
            f"Error redo records:         {f'{redo_errors:,}' if not no_redo else ''}"
        )
        logger.info(f"Redo elapsed time (s):      {redo_time if not no_redo else ''}")
        logger.info("")
        logger.info(f"Total elapsed time (s):     {load_time + redo_time}")

        if not cli_args.withinfo and not os.getenv("SENZING_WITHINFO"):
            pathlib.Path(file_output).unlink(missing_ok=True)

        if not load_errors and not error_recs:
            pathlib.Path(file_errors).unlink(missing_ok=True)

        if ingest_file:
            in_file.close()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_int)

    LONG_RECORD = 300
    MODULE_NAME = pathlib.Path(sys.argv[0]).stem
    PAYLOAD_RECORD = 0
    PAYLOAD_START_TIME = 1
    WORK_STATS_INTERVAL = 60
    do_shutdown = False

    arg_parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="Utility to load Senzing JSON records and process redo records",
        epilog=textwrap.dedent(
            """\
                 Arguments can be specified with either CLI arguments or environment variables, some arguments have
                 default values.

                 The order of precedence for selecting which value to use is:

                   1) CLI Argument
                   2) Environment variable
                   3) Default value if available

                 For additional help and information: https://github.com/Senzing/file-loader/blob/main/README.md

               """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    arg_parser.add_argument(
        "-f",
        "--file",
        action=CustomArgAction,
        default=None,
        metavar="file",
        nargs="?",
        help=textwrap.dedent(
            """\
               Path and name of file to load.

               Default: None, skip loading but still process redo records
               Env Var: SENZING_INPUT_FILE

             """
        ),
    )
    arg_parser.add_argument(
        "-cj",
        "--configJson",
        action=CustomArgAction,
        default=None,
        metavar="config",
        nargs="?",
        type=str,
        help=textwrap.dedent(
            """\
               JSON string of the Senzing engine configuration.

               Default: None
               Env Var: SENZING_ENGINE_CONFIGURATION_JSON

             """
        ),
    )
    arg_parser.add_argument(
        "-w",
        "--withinfo",
        action=CustomArgActionStoreTrue,
        default=False,
        nargs=0,
        help=textwrap.dedent(
            """\
               Produce with info messages and write to a file.

               Default: False
               Env Var: SENZING_WITHINFO

             """
        ),
    )
    arg_parser.add_argument(
        "-t",
        "--debugTrace",
        action=CustomArgActionStoreTrue,
        default=False,
        nargs=0,
        help=textwrap.dedent(
            """\
               Output debug trace information.

               Default: False
               Env Var: SENZING_DEBUG

             """
        ),
    )
    arg_parser.add_argument(
        "-nt",
        "--numThreads",
        action=CustomArgAction,
        default=0,
        metavar="num_threads",
        type=int,
        help=textwrap.dedent(
            """\
               Total number of worker threads performing load.

               Default: Calculated
               Env Var: SENZING_THREADS_PER_PROCESS

             """
        ),
    )
    arg_parser.add_argument(
        "-n",
        "--noRedo",
        action=CustomArgActionStoreTrue,
        default=False,
        nargs=0,
        help=argparse.SUPPRESS,
    )

    cli_args = arg_parser.parse_args()

    # If a CLI arg was specified use it, else try the env var, if no env var use the default for the CLI arg
    # Sets the priority to 1) CLI arg, 2) Env Var 3) Default value
    ingest_file = (
        cli_args.file
        if cli_args.__dict__.get("file_specified")
        else os.getenv("SENZING_INPUT_FILE")
    )

    engine_config = (
        cli_args.configJson
        if cli_args.__dict__.get("configJson_specified")
        else os.getenv("SENZING_ENGINE_CONFIGURATION_JSON", cli_args.configJson)
    )
    with_info = (
        cli_args.withinfo
        if cli_args.__dict__.get("info_specified")
        else arg_convert_boolean("SENZING_WITHINFO", cli_args.withinfo)
    )
    debug_trace = (
        cli_args.debugTrace
        if cli_args.__dict__.get("debugTrace_specified")
        else arg_convert_boolean("SENZING_DEBUG", cli_args.debugTrace)
    )
    num_threads = (
        cli_args.numThreads
        if cli_args.__dict__.get("numThreads_specified")
        else int(os.getenv("SENZING_THREADS_PER_PROCESS", cli_args.numThreads))
    )
    no_redo = (
        cli_args.noRedo
        if cli_args.__dict__.get("noRedo_specified")
        else arg_convert_boolean("SENZING_NO_REDO", cli_args.noRedo)
    )

    errors_file = (
        f'{MODULE_NAME}_errors_{str(datetime.now().strftime("%Y%m%d_%H%M%S"))}.log'
    )
    with_info_file = (
        f'{MODULE_NAME}_withInfo_{str(datetime.now().strftime("%Y%m%d_%H%M%S"))}.jsonl'
    )
    # If running in a container use /data/
    if os.getenv("SENZING_DOCKER_LAUNCHED"):
        errors_file = f"/data/{errors_file}"
        with_info_file = f"/data/{with_info_file}"

    try:
        logger = logging.getLogger(pathlib.Path(sys.argv[0]).stem)
        console_handle = logging.StreamHandler(stream=sys.stdout)
        console_handle.setLevel(logging.INFO)
        file_handle = logging.FileHandler(errors_file, "w")
        file_handle.setLevel(logging.ERROR)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        log_format = "%(asctime)s - %(name)s - %(levelname)s:  %(message)s"
        console_handle.setFormatter(logging.Formatter(log_format))
        file_handle.setFormatter(logging.Formatter(log_format))
        logger.addHandler(console_handle)
        logger.addHandler(file_handle)
    except IOError as ex:
        print(ex)
        sys.exit(-1)

    if not engine_config:
        logger.warning(
            "SENZING_ENGINE_CONFIGURATION_JSON environment variable or --configJson CLI"
            " argument must be set with the engine configuration JSON"
        )
        logger.warning(
            "https://senzing.zendesk.com/hc/en-us/articles/360038774134-G2Module-Configuration-and-the-Senzing-API"
        )
        sys.exit(-1)

    if not ingest_file and no_redo:
        logger.error("No input file and redo processing disabled, nothing to do!")
        sys.exit(-1)

    try:
        sz_engine = SzEngine("pySzEngine", engine_config, verbose_logging=debug_trace)
        sz_diag = SzDiagnostic(
            "pySzDiagnostic", engine_config, verbose_logging=debug_trace
        )
        sz_product = SzProduct(
            "pySzProduct", engine_config, verbose_logging=debug_trace
        )
        sz_configmgr = SzConfigManager(
            "pySzConfigMgr", engine_config, verbose_logging=debug_trace
        )
    except SzError as ex:
        logger.error(ex)
        sys.exit(-1)

    startup_info(sz_engine, sz_diag, sz_configmgr, sz_product)

    load_and_redo(
        sz_engine,
        ingest_file,
        with_info_file,
        errors_file,
        num_threads,
        no_redo,
        with_info,
    )
