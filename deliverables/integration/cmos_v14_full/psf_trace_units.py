"""Read voltage/current TRACE types, including optional PSF property blocks."""
import re


def trace_units(path):
    units = {}
    active = False
    in_properties = False
    with path.open() as stream:
        for line in stream:
            text = line.strip()
            if text == 'TRACE':
                active = True
                continue
            if text == 'VALUE':
                assert not in_properties
                break
            if not active:
                continue
            if in_properties:
                if text == ')':
                    in_properties = False
                continue
            match = re.fullmatch(r'"([^"]+)" "([VI])"(?:\s+(PROP\())?', text)
            assert match, line
            assert match[1] not in units, match[1]
            units[match[1]] = 'A' if match[2] == 'I' else 'V'
            in_properties = bool(match[3])
    assert active and units and not in_properties
    return units
