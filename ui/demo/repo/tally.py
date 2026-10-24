"""tally: a very small expense helper, the sample repo for `closer demo`."""


def total(amounts):
    """Sum of the amounts, rounded to cents."""
    return round(sum(amounts), 2)


def share(amount, people):
    """Equal share of an amount between people, rounded to cents."""
    if people < 1:
        raise ValueError("people must be at least 1")
    return round(amount / people, 2)


def label(amount):
    """An amount as a dollar string."""
    return "$%.2f" % amount
