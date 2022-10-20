import contextlib
import os
import sys
import xml.etree.ElementTree as ET

base_dirs = [
    os.path.join(os.environ['MESON_SOURCE_ROOT'], os.environ['MESON_SUBDIR']),
    os.path.join(os.environ['MESON_BUILD_ROOT'], os.environ['MESON_SUBDIR']),
]
_, prefix, *paths = sys.argv
xml = ET.ElementTree()
root_element = ET.Element('gresources')
xml._setroot(root_element)
resource_element = ET.Element('gresource')
root_element.append(resource_element)
resource_element.set('prefix', prefix)
for path in paths:
    alias = path
    for base_dir in base_dirs:
        with contextlib.suppress(ValueError):
            alias = min(alias, os.path.relpath(path, base_dir), key=len)
    file_element = ET.Element('file')
    resource_element.append(file_element)
    file_element.set('alias', alias)
    file_element.text = path
xml.write(sys.stdout.buffer, encoding='utf-8', xml_declaration=True)
