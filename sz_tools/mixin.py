#! /usr/bin/env python3


# ---- Mixins ----------------------------------------------------------------


class PrintPrefixMixin:
    def do_print(self):
        print(self.prefix)


class PrintAllMixin:
    def do_print(self):
        print(self.prefix, self.text)


class ParentClass:
    def say_hi(self):
        print("Hi")


# ---- Classes ----------------------------------------------------------------


class PrefixClass(ParentClass, PrintPrefixMixin):
    def __init__(self, *args, **kwargs):
        self.prefix = "PREFIX - 1:"
        self.text = "Full text - 1"

    def my_print(self):
        self.say_hi()
        self.do_print()


class AllClass(ParentClass, PrintAllMixin):
    def __init__(self, *args, **kwargs):
        self.prefix = "PREFIX - 2:"
        self.text = "Full text - 2"

    def my_print(self):
        self.say_hi()
        self.do_print()


# ---- Main -------------------------------------------------------------------


x = PrefixClass()
x.my_print()


y = AllClass()
y.my_print()
