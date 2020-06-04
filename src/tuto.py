import turtle as t



def tree(branch_len, depth, angle):
    """Draw a tree from the current position"""

    if depth == 0:
        return None

    t.pensize(depth)
    t.forward(branch_len * depth)
    t.left(angle)
    tree(branch_len, depth - 1, angle)
    t.right(angle * 2)
    tree(branch_len, depth - 1, angle)
    t.left(angle)
    t.penup()
    t.back(branch_len * depth)
    t.pendown()


t.pen(speed=0)

t.left(90)
t.penup()
t.back(200)
t.pendown()
tree(10, depth=8, angle=20)

t.mainloop()
