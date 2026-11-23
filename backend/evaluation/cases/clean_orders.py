def total_price(items):
    return sum(item["price"] * item["quantity"] for item in items)


def average_rating(ratings):
    return sum(ratings) / len(ratings) if ratings else 0.0


def add_tag(tag, tags=None):
    tags = [] if tags is None else tags
    tags.append(tag)
    return tags
