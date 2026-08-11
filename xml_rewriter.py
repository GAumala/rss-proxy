import re

from lxml import etree as ET


# Matches template placeholders like `$title`, `$guid`, or `$torrent:size`.
# The capture group strips the leading `$` so the raw tag name can be looked up.
# It matches things like:
# - $title
# - $custom:field
# - $alt-link
# What the pattern means:
# - \$ = a literal $
# - ([ ... ]) = capture the placeholder name without the $
# - [A-Za-z_] = first character must be a letter or _
# - [\w.-]* = then any number of letters, digits, _, ., or -
# - (?::[A-Za-z_][\w.-]*)? = optional :suffix part, for prefixed names like custom:field
# So in:
# "title": "$title [$custom:field]"
# it finds:
# - title
# - custom:field
# and replaces each with the value pulled from the XML item.
TEMPLATE_PLACEHOLDER_RE = re.compile(r"\$([A-Za-z_][\w.-]*(?::[A-Za-z_][\w.-]*)?)")


class XmlRewriter:
    """Rewrite item fields using template strings.

    Template values may contain placeholders like ``$title``, ``$alt-link``, or
    prefixed names like ``$custom:field``. Each placeholder is replaced with the
    matching value from the current ``<item>`` element.
    """

    def __init__(self, rewrites):
        self.rewrites = rewrites

    def rewrite(self, payload):
        parser = ET.XMLParser(recover=True, huge_tree=True, resolve_entities=False)
        root = ET.fromstring(payload, parser=parser)
        namespaces = self._collect_namespaces(root)
        for item in root.findall(".//item"):
            for target, template in self.rewrites.items():
                element = self._find_or_create_child(item, target, namespaces)
                if element is None:
                    raise ValueError(f"cannot create malformed XML tag '{target}'")
                element.text = self._render_template(str(template), item, namespaces)

        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _collect_namespaces(self, root):
        namespaces = {}
        for element in root.iter():
            for prefix, uri in (element.nsmap or {}).items():
                if prefix:
                    namespaces[prefix] = uri
        return namespaces

    def _qualify(self, tag, namespaces):
        if ":" not in tag:
            return tag
        prefix, local = tag.split(":", 1)
        uri = namespaces.get(prefix)
        if uri is None:
            return tag
        return f"{{{uri}}}{local}"

    def _local_name(self, tag):
        return tag.rsplit("}", 1)[-1] if tag.startswith("{") else tag

    def _find_item_value(self, item, name, namespaces):
        qualified = self._qualify(name, namespaces)

        for child in list(item):
            if child.tag == qualified or child.tag == name or (
                ":" not in name and self._local_name(child.tag) == name
            ):
                return "" if child.text is None else child.text

        for child in item.iter():
            if child is item:
                continue
            if child.tag == qualified or child.tag == name or (
                ":" not in name and self._local_name(child.tag) == name
            ):
                return "" if child.text is None else child.text

        return ""

    def _render_template(self, template, item, namespaces):
        return TEMPLATE_PLACEHOLDER_RE.sub(
            lambda match: self._find_item_value(item, match.group(1), namespaces),
            template,
        )

    def _find_or_create_child(self, item, name, namespaces):
        qualified = self._qualify(name, namespaces)
        for child in list(item):
            if child.tag == qualified or child.tag == name or (
                ":" not in name and self._local_name(child.tag) == name
            ):
                return child
        if ":" in name and qualified == name:
            return None
        return ET.SubElement(item, qualified)
