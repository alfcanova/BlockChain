import io
p = "tests/test_api.py"
src = io.open(p, encoding="utf-8").read()
pairs = [
    ('"cidade_nascimento":"SP"', '"cidade_nascimento":"Sao Paulo"'),
    ('"cidade_nascimento":"RJ"', '"cidade_nascimento":"Rio de Janeiro"'),
]
for old, new in pairs:
    src = src.replace(old, new)
io.open(p, "w", encoding="utf-8").write(src)
print("test_api ok")