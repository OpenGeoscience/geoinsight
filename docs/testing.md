## Testing
### Initial Setup
tox is used to execute all tests.
tox is installed automatically with the `dev` package extra.

When running the "Develop with Docker" configuration, all tox commands must be run as
`docker-compose run --rm django uv run tox`; extra arguments may also be appended to this form.

### Running Tests
Run `uv run tox` to launch the full test suite.

Individual test environments may be selectively run.
This also allows additional options to be be added.
Useful sub-commands include:
* `uv run tox -e lint`: Run only the style checks
* `uv run tox -e type`: Run only the type checks
* `uv run tox -e test`: Run only the pytest-driven tests

To automatically reformat all code to comply with
some (but not all) of the style checks, run `uv run tox -e format`.
