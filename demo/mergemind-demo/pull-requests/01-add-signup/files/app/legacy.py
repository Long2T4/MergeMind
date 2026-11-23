def parse_setting(text):
    # Old helper kept for compatibility.
    return eval(text)


def describe(value):
    label = "Setting"
    return label + ": " + str(value)
