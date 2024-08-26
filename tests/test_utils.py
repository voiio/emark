from emark import utils


class TestNode:
    def test_post_init(self):
        html = utils.Node("html", {}, None)
        body = utils.Node("html", {}, html)
        assert html.parent is None
        assert body.parent == html

    def test_iter(self):
        body = utils.Node("body", {}, None)
        p1 = utils.Node("p", {}, body)
        p2 = utils.Node("p", {}, body)
        assert list(body) == [p1, p2]

    def test_repr(self):
        body = utils.Node("body", {}, None)
        assert repr(body) == "<body/>"

        body = utils.Node("a", {"href": "/highway/to.html"}, None)
        assert repr(body) == '<a href="/highway/to.html"/>'

    def test_str__str(self):
        node = utils.Node("span", {}, None)
        node.children.append("foo")
        assert str(node) == "foo"

    def test_str__block(self):
        node = utils.Node("p", {}, None)
        node.children.append("foo")
        assert str(node) == "foo\n\n"

    def test_str__br(self):
        node = utils.Node("br", {}, None)
        assert str(node) == "\n"

    def test_str__hr(self):
        node = utils.Node("hr", {}, None)
        assert str(node) == "\n--------------------------------------------------\n"

    def test_str__emphasis(self):
        node = utils.Node("em", {}, None)
        node.children.append("foo")
        assert str(node) == "*foo*"

    def test_str__link(self):
        node = utils.Node("a", {"href": "/highway/to.html"}, None)
        assert str(node) == ""
        node.children.append("foo")
        assert str(node) == "foo </highway/to.html>"

    def test_str__img(self):
        node = utils.Node("img", {}, None)
        assert str(node) == ""
        node = utils.Node("img", {"alt": "beautifully lake"}, None)
        assert str(node) == "[image: beautifully lake]"

    def test_str__script(self):
        node = utils.Node("script", {}, None)
        node.children.append("foo")
        assert str(node) == ""

    def test_text(self):
        p = utils.Node("p", {}, None)
        p.children.append("some ")
        strong = utils.Node("strong", {}, p)
        strong.children.append("very important")
        p.children.append(" message")

        assert p.text == "some *very important* message"


class TestHTML2TextParser:
    def test_parse_html_email(self):
        html = """
        <html>
        <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>test</title>
        <style>body {background: #dadada;}</style>
        <script>document.AddEventListener('click', () => {})</script>
        </head>
        <body>
        <h1>Headline</h1>
        <p>Dear,<br/>
        How are you doing?
        </p>
        <a href="no-html-text"><img src="no-alt"></a>
        <img alt="important img" src="path/to.img">
        <a href="http://www.google.com">Link</a>
        <a href="http://www.acme.com">
          <img alt="Pretty flowers" src="path/to.img"/>
        </a>
        <hr>
        <p>some footer</p>
        </body>
        </html>
        """
        parser = utils.HTML2TextParser()
        parser.feed(html)
        assert str(parser) == (
            "Headline\n"
            "\n"
            "Dear,\n"
            "How are you doing?\n"
            "\n"
            "[image: important img] Link <http://www.google.com> [image: Pretty flowers] <http://www.acme.com>\n"
            "--------------------------------------------------\n"
            "some footer"
        )


def test_extract_domain():
    assert utils.extract_domain("https://example.com") == "example.com"
    assert utils.extract_domain("https://www.example.com") == "example.com"
    assert utils.extract_domain("https://www.example.co.uk") == "example.co.uk"
    assert utils.extract_domain("https://www.example.com:1337") == "example.com:1337"
    assert utils.extract_domain("https://localhost") == "localhost"
    assert utils.extract_domain("https://localhost:8000") == "localhost:8000"
