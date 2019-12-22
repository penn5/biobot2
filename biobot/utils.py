def fibgen():
    # https://stackoverflow.com/a/3955269/5509575
    a, b = 0, 1
    while True:
        yield a
        b = a + b
        yield b
        a = a + b
