#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""html.py: Contains functions to modify HTML documents. Mainly we need to
update output HTML reference links at the moment."""
import os
import pypipegraph as ppg
from abc import abstractmethod
from bs4 import BeautifulSoup
from bs4.formatter import Formatter
from pathlib import Path
from typing import Union, Callable, List
from pypipegraph import Job

__author__ = "Marco Mernberger"
__copyright__ = "Copyright (c) 2020 Marco Mernberger"
__license__ = "mit"


# functionality we need:
# replace ref links
# copy the html file for a given output to a report folder and replace
# file links. This should be used from the report alone and work with any html, not just GSEA.


class HTMLModifier:
    def __init__(
        self, output_formatter: Union[str, Formatter] = "html", filename_generator: Callable = None
    ):
        self.parser = "html.parser"
        self.formatter = output_formatter
        self.filename_generator = self._new_suffix
        if filename_generator is not None:
            self.filename_generator = filename_generator
        self._dependencies = [
            ppg.FunctionInvariant(f"{str(self)}_job", self.job),
            ppg.FunctionInvariant(f"{str(self)}_write_html", self.write_html),
            ppg.FunctionInvariant(f"{str(self)}_new_html", self.new_html),
        ]

    def __str__(self):
        return "HTMLModifier"

    def write_html(self, output: Path, soup: BeautifulSoup):
        with output.open("w") as op:
            op.write(soup.prettify(formatter=self.formatter))

    def _new_suffix(self, html: Path) -> Path:
        return html.with_suffix(".modified.html")

    def new_html(self, html: Path) -> Path:
        return self.filename_generator(html)

    @abstractmethod
    def job(self, html: Path, dependencies: List[Job]) -> Job:
        "return a job creating the new html file."
        pass

    @property
    def dependencies(self):
        return self._dependencies


class LinkModifier(HTMLModifier):
    def __init__(
        self,
        modify_link: Callable,
        link_matcher: Union[Callable, str] = None,
        output_formatter: Union[str, Formatter] = "html",
        filename_generator: Callable = None,
    ):
        super().__init__(output_formatter, filename_generator)
        self.modify_link = modify_link
        self.link_matcher = link_matcher
        self._dependencies.extend(
            [
                ppg.FunctionInvariant(f"{str(self)}_modify_link", self.modify_link),
                ppg.FunctionInvariant(f"{str(self)}_get_matcher", self.get_matcher),
                ppg.FunctionInvariant(f"{str(self)}_modify_soup", self.modify_soup),
                ppg.FunctionInvariant(f"{str(self)}_create", self.create),
            ]
        )

    def __str__(self):
        return "LinkModifier"

    def get_matcher(self, html: Path):
        "Returns a function that determines which link to modify."

        def string_matcher(substring: str):
            def match(href: str):
                return substring in href

            return match

        def accept_all(*_):
            return True

        if isinstance(self.link_matcher, str):
            matcher = string_matcher(self.link_matcher)
        elif callable(self.link_matcher):
            matcher = self.link_matcher
        elif self.link_matcher is None:
            matcher = accept_all
        else:
            raise ValueError(
                f"link_matcher must be of [String, Calllable, Nine], was {type(self.link_matcher)}."
            )
        return matcher

    def job(self, html: Path, dependencies: List[Job]) -> Job:
        dependencies.extend(self.dependencies)
        outfile = self.filename_generator(html)

        def __create():
            self.create(html, outfile)

        return ppg.FileGeneratingJob(outfile, __create).depends_on(dependencies)

    def create(self, html: Path, outfile: Path):
        outfile.parent.mkdir(exist_ok=True, parents=True)
        with open(html) as fp:
            soup = BeautifulSoup(fp, self.parser)
            soup = self.modify_soup(soup, self.get_matcher(html), html)
            self.write_html(outfile, soup)

    def modify_soup(
        self, soup: BeautifulSoup, link_matched: Callable, html: Path = None
    ) -> BeautifulSoup:
        if soup is None:
            raise ValueError("Soup was None.")
        for link in soup.find_all("a"):
            href = link.get("href")
            if link_matched(href):
                new_link = self.modify_link(html.parent / href)
                link["href"] = new_link
        return soup


class ReportPathModifier(LinkModifier):
    def __init__(
        self,
        report_path: Path = None,
        link_matcher: Union[Callable, str] = None,
        output_formatter: Union[str, Formatter] = "html",
        filename_generator: Callable = None,
    ):
        self.report_path = Path("out/notebook")
        if report_path is not None:
            self.report_path = report_path
        super().__init__(
            modify_link=self.modify_link,
            link_matcher=link_matcher,
            output_formatter=output_formatter,
            filename_generator=filename_generator,
        )

    def __str__(self):
        return "ReportPathModifier"

    def modify_link(self, href_path: Path):
        return ReportPathModifier.resolve_path(self.report_path, href_path)

    @classmethod
    def resolve_path(self, report_path: Path, result_path: Path) -> Path:
        return_path = Path(os.path.relpath(result_path.resolve(), report_path.resolve()))
        return return_path


class GSEAReportPathModifier(ReportPathModifier):
    def __init__(
        self,
        report_path: Path = None,
        link_matcher: Union[Callable, str] = None,
        output_formatter: Union[str, Formatter] = "html",
        filename_generator: Callable = None,
    ):
        super().__init__(
            report_path=report_path,
            link_matcher=link_matcher,
            output_formatter=output_formatter,
            filename_generator=filename_generator,
        )

    def __str__(self):
        return "GSEAReportPathModifier"

    def get_matcher(self, html: Path):
        folder_name = get_folder_from_gsea_html(html)

        def accept(href: str):
            return folder_name in href

        return accept


def get_folder_from_gsea_html(html: Path):
    with open(html) as fp:
        soup = BeautifulSoup(fp, "html.parser")
        for link in soup.find_all("a"):
            href = link.get("href")
            if "pos_snapshot.html" in href:
                return str(Path(href).parent)
    raise ValueError("Could not scrape the folder name from html, 'pos_snapshot.html' not found.")
