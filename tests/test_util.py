import pytest
import util


# most example values taken from https://stackoverflow.com/a/60708339 
@pytest.mark.parametrize("input,expected_size", [
    ('1024b', 1024),
    ('10.43 KB', 10680),
    ('11 GB', 11811160064),
    ('343.1 MB', 359766425),
    ('10.43KB', 10680),
    ('11GB', 11811160064),
    ('343.1MB', 359766425),
    ('10.43 kb', 10680),
    ('11 gb', 11811160064),
    ('343.1 mb', 359766425),
    ('10.43kb', 10680),
    ('11gb', 11811160064),
    ('343.1mb', 359766425),
    (-1, -1),
    (0, 0),
    (1234567, 1234567),
    ('1984', 1984)
])

def test_parse_size(input, expected_size):
    assert util.parse_size(input) == expected_size

#TODO: test invalid input properly raises exception