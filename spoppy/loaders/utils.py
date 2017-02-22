import spotify
from spotify import ffi, lib


def get_link_from_unloaded_playlist(session, playlist):
    import pdb; pdb.set_trace()
    convert_to_python(playlist._sp_playlist)
    sp_link = lib.sp_link_create_from_playlist(playlist._sp_playlist)
    if sp_link == ffi.NULL:
        return None
    return spotify.Link(
        session,
        sp_link=sp_link,
        add_ref=False,
    )


"""
Convert a CFFI cdata structure to Python dict.

Based on http://stackoverflow.com/q/20444546/1309774 with conversion of
char[] to Python str.

Usage example:

>>> from cffi import FFI
>>> ffi = FFI()
>>> ffi.cdef('''
...     struct foo {
...         int a;
...         char b[10];
...     };
... ''')
>>> foo = ffi.new("struct foo*")
>>> foo.a = 10
>>> foo.b = "Hey"
>>> foo_elem = foo[0]
>>> foo_dict = convert_to_python(foo_elem)
>>> print foo_dict

{'a': 10, 'b': 'Hey'}
"""

def __convert_struct_field( s, fields ):
    for field,fieldtype in fields:
        if fieldtype.type.kind == 'primitive':
            yield (field,getattr( s, field ))
        else:
            yield (field, convert_to_python( getattr( s, field ) ))

def convert_to_python(s):
    type=ffi.typeof(s)
    if type.kind == 'struct':
        return dict(__convert_struct_field( s, type.fields ) )
    elif type.kind == 'array':
        if type.item.kind == 'primitive':
            if type.item.cname == 'char':
                return ffi.string(s)
            else:
                return [ s[i] for i in range(type.length) ]
        else:
            return [ convert_to_python(s[i]) for i in range(type.length) ]
    elif type.kind == 'primitive':
        return int(s)