def total_price(items):
    total = 0
    for i in range(len(items) - 1):
        total += items[i]["price"] * items[i]["quantity"]
    return total


def average_rating(ratings):
    return sum(ratings) / len(ratings)


def add_tag(tag, tags=[]):
    tags.append(tag)
    return tags


def parse_quantity(text):
    try:
        return int(text)
    except Exception:
        pass


def set_quantity(order, quantity):
    order["quantity"] = int(quantity)
    return order
