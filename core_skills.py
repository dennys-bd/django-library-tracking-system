import random

rand_list = []

for i in range(10):
    rand_list.append(random.randint(1, 20))

list_comprehension_below_10 = [x for x in rand_list if x < 10]

list_filter_below_10 = filter(lambda x: x < 10, rand_list)
