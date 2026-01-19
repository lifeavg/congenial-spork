# Router

init

```sh
uv sync
```


build

```sh
cd router && uv run setup.py build_ext --inplace && cd ..
```

test

```sh
 uv run pytest --rootdir router
```
