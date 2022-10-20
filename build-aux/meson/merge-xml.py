import sys
import xml.etree.ElementTree as ET


class CommentTreeBuilder(ET.TreeBuilder):
    def comment(self, data):
        self.start(ET.Comment, {})
        self.data(data)
        self.end(ET.Comment)


def make_xml_parser():
    return ET.XMLParser(target=CommentTreeBuilder())


_, main_xml_path, insert_xml_path, insert_xpath = sys.argv
main_xml = ET.parse(main_xml_path, parser=make_xml_parser())
insert_xml = ET.parse(insert_xml_path, parser=make_xml_parser())
main_xml.find(insert_xpath).append(insert_xml.getroot())
main_xml.write(sys.stdout.buffer, encoding='utf-8', xml_declaration=True)
