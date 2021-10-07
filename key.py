def user_pwd():
    fp = open("data/key.txt")
    for i, line in enumerate(fp):
        if i == 1:
            pwd = line
        elif i == 0:
            user_name = line
        elif i == 2:
            sw_user_name = line
    fp.close()
    return [user_name.strip(), pwd, sw_user_name]
