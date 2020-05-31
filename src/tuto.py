

str = "1010"

base = 2
n = 0  # nombre final

for i in range(0, len(str)):
    c = int(str[-1 - i])
    n = n + c * (base ** i)


print(n)







5..500

#     100 10  1
# i   10² 10¹




