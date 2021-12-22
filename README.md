# Rembrain Robot Framework

Instructions will be soon.

#### Lint
`pycodestyle . --config=config/.pycodestyle`

#### Tests:
`pytest -c config/pytest.ini -n 8`

#### Building docs:
Install requirements from config/requirements/docs.txt then
```shell
cd docs
make html
```

This will result in a `build/html` folder to be generated with the Sphinx documentation project

#### Examples
Instructions [here](examples/README.md)
