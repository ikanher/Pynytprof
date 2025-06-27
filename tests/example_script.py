def work():
    total = 0
    for i in range(10_000):
        total += i * i
    return total

if __name__ == '__main__':
    print(work())
