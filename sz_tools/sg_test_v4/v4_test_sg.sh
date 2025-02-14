rm sg_snapshot_v40.*
rm sg_audit_v39-v40.*
echo YESPURGESENZING | sz_command -C purge_repository
sz_configtool -f sg_config.g2c 
sz_file_loader -f Singapore_File_1.json
sz_file_loader -f Singapore_File_2.json
sz_file_loader -f Singapore_File_3.json
sz_snapshot3 -QAo sg_snapshot_v40
sz_audit -p sg_snapshot_v39.csv -n sg_snapshot_v40.csv -o sg_audit_v39-v40
sz_explorer -s sg_snapshot_v40.json -a sg_audit_v39-v40.json

 
