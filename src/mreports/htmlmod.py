#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""html.py: Contains functions to modify HTML documents. Mainly we need to
update output HTML reference links at the moment."""
import os
import pypipegraph2 as ppg2
from abc import abstractmethod
from bs4 import BeautifulSoup
from bs4.formatter import Formatter
from pathlib import Path
from typing import Union, Callable, List, Optional
from pypipegraph2 import Job

__author__ = "Marco Mernberger"
__copyright__ = "Copyright (c) 2020 Marco Mernberger"
__license__ = "mit"


class HTMLModifier:
    def __init__(
        self,
        output_formatter: Union[str, Formatter] = "html",
        filename_generator: Optional[Callable] = None,
    ):
        """
        __init__ _summary_

        _extended_summary_

        Parameters
        ----------
        output_formatter : Union[str, Formatter], optional
            output formatter for beautiful soup, by default "html".
        filename_generator : Optional[Callable], optional
            A callable that determines the Path of the modified html file, by
            default None. If None, the default is to append a suffix to the original
            path.
        """
        self.parser = "html.parser"
        self.formatter = output_formatter
        self.filename_generator = self._new_suffix
        if filename_generator is not None:
            self.filename_generator = filename_generator
        self._dependencies = [
            ppg2.FunctionInvariant(f"{str(self)}_job", self.job),
            ppg2.FunctionInvariant(f"{str(self)}_write_html", self.write_html),
            ppg2.FunctionInvariant(f"{str(self)}_new_html", self.new_html),
        ]

    def __str__(self):
        return "HTMLModifier"

    def write_html(self, output: Path, soup: BeautifulSoup):
        """
        Writes an html from a given instance of BeautifulSoup.

        Parameters
        ----------
        output : Path
            Path of the new output html.
        soup : BeautifulSoup
            BeautifulSoup isntance with html content to write.
        """
        with output.open("w") as op:
            op.write(soup.prettify(formatter=self.formatter))

    def _new_suffix(self, html: Path, suffix: str = ".modified.html") -> Path:
        """
        Modifies a given Path by adding a suffix.

        Parameters
        ----------
        html : Path
            Original Path.

        Returns
        -------
        Path
            Modified Path.
        """
        return html.with_suffix(suffix)

    def new_html(self, html: Path) -> Path:
        """
        Returns a modified Path based on the filename generator attribute.

        The default filename generator takes a path a and returns a modified
        path with an added suffix by invoking self._new_suffix.

        Parameters
        ----------
        html : Path
            Original path.

        Returns
        -------
        Path
            modified Path.
        """
        return self.filename_generator(html)

    @abstractmethod
    def job(self, html: Path, dependencies: List[Job]) -> Job:
        "return a job creating the new html file."
        pass

    @property
    def dependencies(self) -> List[Job]:
        """
        Returns a list of dependency jobs.

        Returns
        -------
        List[Job]
            List of dependency jobs.
        """
        return self._dependencies


class LinkModifier(HTMLModifier):
    """
    HTMLmodifier to modify links in an html document and return a new file.

    Parameters
    ----------
    modify_link : Callable
        function that modifies the links.
    link_matcher : Union[Callable, str, None], optional
        function that determines which link to modify, by default None
    output_formatter : Union[str, Formatter], optional
        output formatter for beautiful soup, by default "html".
    filename_generator : Optional[Callable], optional
        A callable that determines the Path of the modified html file, by
        default None. If None, the default is to append a suffix to the original
        path.
    """

    def __init__(
        self,
        modify_link: Callable,
        link_matcher: Union[Callable, str, None] = None,
        output_formatter: Union[str, Formatter] = "html",
        filename_generator: Optional[Callable] = None,
    ):
        """Constructor."""
        super().__init__(output_formatter, filename_generator)
        self.modify_link = modify_link
        self.link_matcher = link_matcher
        self._dependencies.extend(
            [
                ppg2.FunctionInvariant(f"{str(self)}_modify_link", self.modify_link),
                ppg2.FunctionInvariant(f"{str(self)}_get_matcher", self.get_matcher),
                ppg2.FunctionInvariant(f"{str(self)}_modify_soup", self.modify_soup),
                ppg2.FunctionInvariant(f"{str(self)}_create", self.create),
            ]
        )

    def __str__(self):
        return "LinkModifier"

    def get_matcher(self, *args) -> Callable:
        """
        Returns a function that determines which link to modify. The actual function
        to be used is determined by the link_matcher attribute.

        Returns
        -------
        Callable
            A function that determines for a given link if it should be modified.
        """

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
        """
        Returns a job that creates a new modified file.

        Returns a pipegraph job that performs the modification and creation
        of the new file. Encapsulates self.create.

        Parameters
        ----------
        html : Path
            Path to original file.
        dependencies : List[Job]
            List of dependency jobs.

        Returns
        -------
        Job
            Job that creates the file.
        """
        dependencies.extend(self.dependencies)
        outfile = self.filename_generator(html)

        def __create(outfile):
            self.create(html, outfile)

        return ppg2.FileGeneratingJob(outfile, __create).depends_on(dependencies)

    def create(self, html: Path, outfile: Path) -> None:
        """
        This creates the modified file.

        _extended_summary_

        Parameters
        ----------
        html : Path
            Path to original file.
        outfile : Path
            Path to new modified file.
        """

        outfile.parent.mkdir(exist_ok=True, parents=True)
        with open(html) as fp:
            soup = BeautifulSoup(fp, self.parser)
            soup = self.modify_soup(soup, self.get_matcher(html), html)
            self.write_html(outfile, soup)

    def modify_soup(
        self, soup: BeautifulSoup, link_matched: Callable, html: Optional[Path] = None
    ) -> BeautifulSoup:
        """
        Modifies a BeatifulSoup instance and returns a new modified instance thereof.

        Modifies a given BeautifulSoup instance by replacing/modifying links
        from the original html document.

        Parameters
        ----------
        soup : BeautifulSoup
            original soup.
        link_matched : Callable
            A callable that determines if a link should be modified.
        html : Optional[Path], optional
            Path to original html file, by default None.

        Returns
        -------
        BeautifulSoup
            _description_

        Raises
        ------
        ValueError
            _description_
        """
        if soup is None:
            raise ValueError("Soup was None.")
        for link in soup.find_all("a"):
            href = link.get("href")
            if link_matched(href):
                new_link = str(self.modify_link(Path(href)))
                link["href"] = new_link
        return soup


class ReportPathModifier(LinkModifier):
    def __init__(
        self,
        report_path: Optional[Path] = None,
        link_matcher: Union[Callable, str, None] = None,
        output_formatter: Union[str, Formatter] = "html",
        filename_generator: Optional[Callable] = None,
    ):
        """
        Generates a report file with

        _extended_summary_

        Parameters
        ----------
        report_path : Optional[Path], optional
            Path to report folder, where a new html is created, by default None.
        link_matcher : Union[Callable, str, None], optional
           function that determines which link to modify, by default None.
        output_formatter : Union[str, Formatter], optional
            output formatter for beautiful soup, by default "html".
        filename_generator : Optional[Callable], optional
            A callable that determines the Path of the modified html file, by
            default None. If None, the default is to append a suffix to the original
            path.
        """
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
        """
        Modifies a Path object relative to self.report_path.

        Parameters
        ----------
        href_path : Path
            The path to be modified.

        Returns
        -------
        _type_
            The updated path.
        """
        return ReportPathModifier.resolve_path(self.report_path, href_path)

    @classmethod
    def resolve_path(self, report_path: Path, result_path: Path) -> Path:
        """
        Returns a new path for the result_path relative to the report_path.

        This is used to update relative paths so files in report path can be
        accessed from report path.

        Parameters
        ----------
        report_path : Path
            Path to link from.

        result_path : Path
            Path of files to link to.

        Returns
        -------
        Path
            A new Path for result_path relative to report_path.
        """
        return_path = Path(os.path.relpath(result_path.resolve(), report_path.resolve()))
        return return_path


class GSEAReportPathModifier(ReportPathModifier):
    """
    Convenience class to fix links in GSEA output for the report file.

    Parameters
    ----------
    report_path : Optional[Path], optional
        Path to report folder, where a new html is created, by default None.
    link_matcher : Union[Callable, str, None], optional
        function that determines which link to modify, by default None.
    output_formatter : Union[str, Formatter], optional
        output formatter for beautiful soup, by default "html".
    filename_generator : Optional[Callable], optional
        A callable that determines the Path of the modified html file, by
        default None. If None, the default is to append a suffix to the original
        path.
    """

    def __init__(
        self,
        report_path: Optional[Path] = None,
        link_matcher: Union[Callable, str, None] = None,
        output_formatter: Union[str, Formatter] = "html",
        filename_generator: Optional[Callable] = None,
    ):
        """Constructor."""
        super().__init__(
            report_path=report_path,
            link_matcher=link_matcher,
            output_formatter=output_formatter,
            filename_generator=filename_generator,
        )

    def __str__(self):
        return "GSEAReportPathModifier"

    def get_matcher(self, html: Path) -> Callable:
        """
        Matches file links in GSEA output index.html.

        Parameters
        ----------
        html : Path
            Path to GSEA index html.

        Returns
        -------
        Callable
            Callable that identifies file links to GSEA folder in GSEA index.html.
        """
        folder_name = get_folder_from_gsea_html(html)

        def accept(href: str):
            return folder_name in href

        return accept


def get_folder_from_gsea_html(html: Path) -> str:
    """
    Retrieves the file folder from GSEA index.html.

    _extended_summary_

    Parameters
    ----------
    html : Path
        Path to index.html.

    Returns
    -------
    str
        The file folder of all GSEA output files.

    Raises
    ------
    ValueError
        If no folder could be found.
    """
    with open(html) as fp:
        soup = BeautifulSoup(fp, "html.parser")
        for link in soup.find_all("a"):
            href = link.get("href")
            if "pos_snapshot.html" in href:
                return str(Path(href).parent)
    raise ValueError("Could not scrape the folder name from html, 'pos_snapshot.html' not found.")
