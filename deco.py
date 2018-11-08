#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import update_wrapper


def disable(func):
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable

    '''
    def wrapper(*args):
        return func(*args)

    return wrapper


def decorator(func):
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''
    def wrapper(*args):
        return func(*args)

    return update_wrapper(wrapper, func)


def countcalls(func):
    '''Decorator that counts calls made to the function decorated.'''
    def wrapper(*args):
        wrapper.calls += 1
        return func(*args)

    wrapper.calls = 0
    return update_wrapper(wrapper, func)


def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    def wrap_mem(*arg):
        res = func.mem_dict.get(arg)
        if not res:
            res = func(*arg)
            func.mem_dict[arg] = res
        return res
    func.mem_dict = {}
    return update_wrapper(wrap_mem, func)


def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''
    def wrap_ar(*args):
        if len(args) == 1:
            return args[0]
        elif len(args) == 2:
            return func(*args)
        while len(args) > 2:
            res_arg = func(args[0], args[1])
            args = (res_arg,) + args[2:]

        return func(*args)

    return update_wrapper(wrap_ar, func)


def trace(dec_arg):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''
    def decorator(func):
        def wrapper(arg):
            print dec_arg*wrapper.ind + " --> %s(%r)" % (func.__name__, arg)
            wrapper.ind += 1
            vl = func(arg)
            if vl:
                wrapper.ind -= 1
                print dec_arg*wrapper.ind + " <-- %s(%r) == %r" % (func.__name__, arg, vl)
            return func(arg)

        wrapper.ind = 0
        return update_wrapper(wrapper, func)

    return decorator


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


@countcalls
@trace("####")
@memo
def fib(n):
    """Some doc"""
    return 1 if n <= 1 else fib(n-1) + fib(n-2)


def main():
    print foo(4, 3)
    print foo(4, 3, 2)
    print foo(4, 3)
    print "foo was called", foo.calls, "times"

    print bar(4, 3)
    print bar(4, 3, 2)
    print bar(4, 3, 2, 1)
    print "bar was called", bar.calls, "times"

    print fib.__doc__
    fib(3)
    print fib.calls, 'calls made'


if __name__ == '__main__':
    main()
