# -*- coding: utf-8 -*-
import pytest
import pypipegraph as ppg
import os
from mreports.htmlmod import (
    HTMLModifier,
    GSEAReportPathModifier,
    LinkModifier,
    ReportPathModifier,
    get_folder_from_gsea_html,
)
from bs4 import BeautifulSoup
from pathlib import Path

__author__ = "MarcoMernberger"
__copyright__ = "MarcoMernberger"
__license__ = "mit"


gsea_html_file = Path("tests") / "data" / "test.html"


def pt_modify_link(href, *args):
    return href[:-4]


def test_htmlmodifier_init():
    mod = HTMLModifier()
    assert mod.parser == "html.parser"
    assert mod.formatter == "html"
    assert mod.filename_generator.__name__ == mod._new_suffix.__name__
    assert callable(mod.filename_generator)
    mod = HTMLModifier("formatter", lambda x: x[:1])
    assert mod.formatter == "formatter"
    assert callable(mod.filename_generator)
    assert mod.filename_generator("ABC") == "A"


def test_htmlmodifier_write_html(tmp_path):
    mod = HTMLModifier(output_formatter="html")
    out = Path("tmp_path") / "test"
    out.parent.mkdir(exist_ok=True, parents=True)
    assert gsea_html_file.exists()
    with open(gsea_html_file) as fp:
        soup = BeautifulSoup(fp, "html.parser")
        mod.write_html(out, soup)
        assert out.exists()


def test_htmlmodifier_new_suffix():
    mod = HTMLModifier()
    assert mod._new_suffix(Path("test.html")) == Path("test.modified.html")


def test_htmlmodifier_filename_generator():
    mod = HTMLModifier(filename_generator=lambda x: x[:2])
    assert mod.filename_generator("test.html") == "te"


def test_linkmodifier_modify_soup(tmp_path):
    out = tmp_path / "test"
    filename_generator = lambda _: out  # noqa: Fxyz
    mod = LinkModifier(pt_modify_link, filename_generator=filename_generator)
    link_matched = lambda x: "202202231319" in x  # noqa: Fxyz
    with open(gsea_html_file) as fp:
        with open(gsea_html_file) as fp2:
            original_soup = BeautifulSoup(fp, "html.parser")
            soup = BeautifulSoup(fp2, "html.parser")
            soup_refs = []
            modified_soup_refs = []
            print(">>>>>>>", type(soup))
            mod.modify_soup(soup, link_matched)
            for link in original_soup.find_all("a"):
                href = link.get("href")
                if link_matched(href):
                    soup_refs.append(href[:-4])
            for link in soup.find_all("a"):
                href = link.get("href")
                if link_matched(href):
                    modified_soup_refs.append(href)
            for sl, ml in zip(soup_refs, modified_soup_refs):
                assert sl == ml


def test_linkmodifier_init():
    mod = LinkModifier(pt_modify_link)
    assert callable(mod.modify_link)
    assert mod.link_matcher is None
    assert mod.formatter == "html"
    assert callable(mod.filename_generator)
    assert hasattr(mod, "_new_suffix")


@pytest.mark.usefixtures("new_pipegraph")
def test_linkmodifier_job(tmp_path):
    out = tmp_path / "test"
    filename_generator = lambda _: out  # noqa: Fxyz
    mod = LinkModifier(pt_modify_link, filename_generator=filename_generator)
    input_file = Path("../../..") / gsea_html_file  # because of the fixture
    assert input_file.exists()
    mod.job(input_file, [])
    ppg.run_pipegraph()
    assert out.exists()


def test_linkmodifier_get_matcher():
    mod = LinkModifier(pt_modify_link)
    matcher = mod.get_matcher(gsea_html_file)
    assert matcher.__name__ == "accept_all"
    assert matcher("something")
    mod = LinkModifier(pt_modify_link, "thing")
    matcher = mod.get_matcher(gsea_html_file)
    assert matcher.__name__ == "match"
    assert matcher("something")
    assert not matcher("not")
    mod = LinkModifier(pt_modify_link, lambda x: "not" in x)
    matcher = mod.get_matcher(gsea_html_file)
    assert not matcher("something")
    assert matcher("not")
    with pytest.raises(ValueError):
        mod = LinkModifier(pt_modify_link, link_matcher=32)
        matcher = mod.get_matcher(gsea_html_file)


def test_linkmodifier_create(tmp_path):
    out = tmp_path / "test" / "test.html"
    filename_generator = lambda _: out  # noqa: Fxyz
    mod = LinkModifier(pt_modify_link, filename_generator=filename_generator)
    mod.create(gsea_html_file, out)
    assert out.exists()


def test_reportpathmodifier_init(tmp_path):
    out = tmp_path / "data" / "test.html"
    filename_generator = lambda _: out  # noqa: Fxyz
    mod = ReportPathModifier()
    assert mod.report_path == Path("out/notebook")
    assert mod.link_matcher is None
    assert mod.formatter == "html"
    assert mod.filename_generator is not None
    assert mod.filename_generator.__name__ == "_new_suffix"
    rep_path = tmp_path / "report" / "test"
    mod = ReportPathModifier(
        report_path=rep_path,
        link_matcher="123",
        filename_generator=filename_generator,
    )
    assert mod.report_path == rep_path
    assert mod.link_matcher == "123"
    assert mod.formatter == "html"
    assert mod.filename_generator == filename_generator


def test_reportpathmodifier_resolve_path(tmp_path):
    report_path = tmp_path / "report" / "test"
    result_path = tmp_path / "data" / "test.html"
    modified_path = ReportPathModifier.resolve_path(report_path, result_path)
    assert modified_path == Path("../../data/test.html")
    report_path = tmp_path / "report" / "test"
    result_path = tmp_path / "report" / "test" / "data" / "test.html"
    modified_path = ReportPathModifier.resolve_path(report_path, result_path)
    assert modified_path == Path("data/test.html")
    report_path = tmp_path / "data" / "report" / "test"
    result_path = tmp_path / "data" / "test.html"
    modified_path = ReportPathModifier.resolve_path(report_path, result_path)
    assert modified_path == Path("../../test.html")


def test_reportpathmodifier_modify_link(tmp_path):
    report_path = tmp_path / "report" / "test"
    mod = ReportPathModifier(report_path)
    href = tmp_path / "data" / "test.html"
    modified_path = mod.modify_link(href, tmp_path / "source.html")
    assert modified_path == Path("../../data/test.html")


def test_gsea_reportpathmodifier_init(tmp_path):
    report_path = tmp_path / "report" / "test"
    mod = GSEAReportPathModifier(
        report_path,
        link_matcher="202202231319",
        output_formatter="html",
        filename_generator=None,
    )
    assert mod.report_path == report_path
    assert mod.link_matcher == "202202231319"
    assert mod.formatter == "html"


def test_gsea_reportpathmodifier_get_matcher(tmp_path):
    report_path = tmp_path / "report" / "test"  # noqa: Fxyz
    mod = GSEAReportPathModifier(
        report_path,
        link_matcher="202202231319",
        output_formatter="html",
        filename_generator=None,
    )
    matcher = mod.get_matcher(gsea_html_file)
    assert matcher("202202231319_bla")
    assert not matcher("202___319_bla")


def test_get_folder_from_gsea_html(tmp_path):
    for ll in Path(".").iterdir():
        print(ll)
    folder = get_folder_from_gsea_html(gsea_html_file)
    assert folder == "202202231319"


def test_as_it_should_work(tmp_path):
    os.chdir(tmp_path)  # this would be the project path
    sub = Path(
        "results/GSEA/Genes_Homo_sapiens_104_canonical_biotypes_1samples%3E=1/EF-MSC-minusSKI-primed_vs_EF-MSC-unprimed/h.all.v7.1"
    )
    data_path = sub
    href = Path("202202231319/pos_snapshot.html")
    index_html = data_path / "index.html"
    report_path = Path("report") / "out"
    report_path.mkdir(parents=True, exist_ok=True)
    href_with_index_filepath = index_html.parent / href
    modified_path = ReportPathModifier.resolve_path(report_path, href_with_index_filepath)
    path_we_need = Path("..") / ".." / sub / href
    assert modified_path == path_we_need
