def unsafe(cursor, name, uid, email):
    by_name = f"SELECT * FROM users WHERE name = '{name}'"
    by_email = "SELECT id FROM users WHERE email = '%s'" % email
    cursor.execute("DELETE FROM users WHERE id = " + uid)
    rename = "UPDATE users SET name = '{}'".format(name)
    log = f'INSERT INTO logs VALUES ({uid})'
    return by_name, by_email, rename, log


def safe(cursor, uid):
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (uid,))
    print(f"Selected {uid}")
    label = f"select one: {uid}"
    note = "update your settings: %s" % uid
    return label, note
