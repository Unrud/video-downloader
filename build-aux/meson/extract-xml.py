import io
import sys
import xml.etree.ElementTree as ET
from xml.sax import saxutils


class CommentTreeBuilder(ET.TreeBuilder):
    def comment(self, data):
        self.start(ET.Comment, {})
        self.data(data)
        self.end(ET.Comment)


def make_xml_parser():
    return ET.XMLParser(target=CommentTreeBuilder())


_, *flags, xml_path, search_xpath = sys.argv
xml = ET.parse(xml_path, parser=make_xml_parser())
for element in xml.findall(search_xpath):
    xml._setroot(element)
    f = io.StringIO()
    xml.write(f, encoding='unicode')
    xml_text = f.getvalue()
    if '--escape' in flags:
        xml_text = saxutils.escape(xml_text)
    sys.stdout.buffer.write(xml_text.encode('utf-8'))
