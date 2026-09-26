import io, re, glob

files = ["tests/test_chain.py", "tests/test_graph.py", "tests/test_new_events.py",
         "tests/test_edge_cases.py", "tests/test_api.py", "tests/test_predictor.py",
         "tests/test_events.py", "tests/test_im.py"]
short = {"SP", "RJ", "MG", "BA", "PE", "CE", "RS", "PR", "DF", "GO", "ES", "PA", "SC"}
for f in files:
    src = io.open(f, encoding="utf-8").read()
    for ln, line in enumerate(src.splitlines(), 1):
        if not re.search(r"\b(cidade|cidade_nascimento|endereco_cidade|cidade_obito|cidade\w*)\b", line):
            continue
        for m in re.finditer(r"[\x27\x22]\b(SP|RJ|MG|BA|PE|CE|RS|PR|DF|GO|ES|PA|SC)[\x27\x22]", line):
            print(f"{f}:{ln}: {line.strip()[:140]}")
            break