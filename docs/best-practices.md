# Best practices

## README.md

1. Use [Markdown lint] to adhere to [Markdown rules].

## Dockerfile

1. Use best practices:
   1. Docker's [Best practices for writing Dockerfiles].
1. Use "lint" when applicable.

   1. Online linter: [FROM: latest]
   1. GitHub [projectatomic/dockerfile_lint] using Docker

      ```console
      sudo docker run -it \
        --rm \
        --privileged \
        --volume $PWD:/root/ \
        projectatomic/dockerfile-lint \
          dockerfile_lint -f Dockerfile
      ```

   1. **Note:** Linters may erroneously report "ARG before FROM" which is supported as of
      [Enterprise Edition 17.06.01] and [Community Edition 17.05.0].

## CONTRIBUTING.md

1. Modifications:

   1. Change following value to appropriate Git repository name.

      ```markdown
      export GIT_REPOSITORY=template-python
      ```

[Best practices for writing Dockerfiles]: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
[Community Edition 17.05.0]: https://docs.docker.com/engine/release-notes/#17050-ce
[Enterprise Edition 17.06.01]: https://docs.docker.com/engine/release-notes/#17061-ee-1
[FROM: latest]: https://www.fromlatest.io
[Markdown lint]: https://dlaa.me/markdownlint/
[Markdown rules]: https://github.com/DavidAnson/markdownlint/blob/master/doc/Rules.md
[projectatomic/dockerfile_lint]: https://github.com/projectatomic/dockerfile_lint
