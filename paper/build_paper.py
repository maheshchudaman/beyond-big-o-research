#!/usr/bin/env python3
"""Build the evidence-based Mac pilot manuscript from generated metrics."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
GENERATED = PAPER / "generated"
OUTPUT = PAPER / "Beyond_Big_O_Mac_Pilot_Study_Draft.docx"
METRICS = json.loads((GENERATED / "paper_metrics.json").read_text(encoding="utf-8"))

BLUE = "2E74B5"
DARK_BLUE = "0B2545"
MID_BLUE = "1F4D78"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F2F4F7"
MUTED = "5E6B78"
WHITE = "FFFFFF"
RISK = "9B1C1C"


def set_run(run, size=11, bold=False, italic=False, color=DARK_BLUE, font="Calibri"):
    run.font.name = font
    rpr = run._element.get_or_add_rPr()
    rpr.rFonts.set(qn("w:ascii"), font)
    rpr.rFonts.set(qn("w:hAnsi"), font)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    node = tc_pr.find(qn("w:shd"))
    if node is None:
        node = OxmlElement("w:shd")
        tc_pr.append(node)
    node.set(qn("w:fill"), fill)


def margins(cell, top=80, start=120, bottom=80, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{side}"))
        if node is None:
            node = OxmlElement(f"w:{side}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    node = OxmlElement("w:tblHeader")
    node.set(qn("w:val"), "true")
    tr_pr.append(node)


def table_geometry(table, widths, indent=120):
    total = sum(widths)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(indent))
    tbl_ind.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        node = OxmlElement("w:gridCol")
        node.set(qn("w:w"), str(width))
        grid.append(node)
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Inches(width / 1440)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            margins(cell)


def add_para(doc, text="", *, size=11, bold=False, italic=False, color=DARK_BLUE, align=None, before=0, after=8, line=1.333, keep=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = line
    p.paragraph_format.keep_with_next = keep
    if align is not None:
        p.alignment = align
    set_run(p.add_run(text), size=size, bold=bold, italic=italic, color=color)
    return p


def add_rich_para(doc, parts, *, after=8, line=1.333, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = line
    for text, options in parts:
        set_run(p.add_run(text), **options)
    return p


def heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.add_run(text)
    p.paragraph_format.keep_with_next = True
    return p


def bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.left_indent = Inches(0.375)
    p.paragraph_format.first_line_indent = Inches(-0.194)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.208
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_run(p.add_run(text))
    return p


def add_table(doc, caption, headers, rows, widths, font_size=9.2):
    add_para(doc, caption, size=9.5, bold=True, color=MID_BLUE, before=4, after=4, keep=True)
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        shade(cell, BLUE)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        set_run(p.add_run(header), size=font_size, bold=True, color=WHITE)
    repeat_header(table.rows[0])
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for index, value in enumerate(values):
            if row_index % 2:
                shade(cells[index], LIGHT_GRAY)
            p = cells[index].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            if index > 1 and len(value) < 16:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_run(p.add_run(value), size=font_size)
    table_geometry(table, widths)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_note(doc, label, text, risk=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.left_indent = Inches(0.15)
    p.paragraph_format.right_indent = Inches(0.15)
    p.paragraph_format.line_spacing = 1.25
    ppr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "FCE8E6" if risk else LIGHT_BLUE)
    ppr.append(shd)
    set_run(p.add_run(f"{label}: "), bold=True, color=RISK if risk else MID_BLUE)
    set_run(p.add_run(text))


def add_picture(doc, path, caption, alt_text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    inline = run.add_picture(str(path), width=Inches(6.3))._inline
    doc_pr = inline.docPr
    doc_pr.set("descr", alt_text)
    doc_pr.set("title", caption.split(".")[0])
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(9)
    cap.paragraph_format.keep_with_next = False
    set_run(cap.add_run(caption), size=9, italic=True, color=MUTED)


def page_number(paragraph):
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr, fld_char2])
    set_run(run, size=8.5, color=MUTED)


def configure(doc):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(DARK_BLUE)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.333

    tokens = {
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 12, 6),
        "Heading 3": (12, MID_BLUE, 8, 4),
    }
    for name, (size, color, before, after) in tokens.items():
        style = doc.styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    for name in ("List Bullet", "List Number"):
        style = doc.styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.208

    header = section.header.paragraphs[0]
    header.paragraph_format.space_after = Pt(0)
    set_run(header.add_run("BEYOND BIG-O  |  APPLE-SILICON PILOT STUDY"), size=8.5, bold=True, color=MUTED)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_run(footer.add_run("Draft manuscript  |  Page "), size=8.5, color=MUTED)
    page_number(footer)


def fmt_ms(value):
    if value < 0.001:
        return f"{value * 1000:.3f} us"
    if value < 1:
        return f"{value:.4f} ms"
    return f"{value:.3f} ms"


def build():
    doc = Document()
    configure(doc)

    # Academic title block (memo_masthead-inspired override).
    add_para(doc, "ORIGINAL RESEARCH - PILOT STUDY", size=9.5, bold=True, color=BLUE, before=4, after=7)
    add_para(doc, "Beyond Big-O: A Reproducible Apple-Silicon Pilot Study of Runtime Performance for Common Data Structures in Python and C++", size=22, bold=True, color=DARK_BLUE, after=9, line=1.08)
    add_para(doc, "Mahesh Patil and Student Research Team", size=12, bold=True, color=MID_BLUE, after=2)
    add_para(doc, "Affiliation to be added before submission", size=10, italic=True, color=MUTED, after=12)
    add_note(doc, "Draft status", "Prepared from measurements executed in Codex on 23 August 2026. This manuscript is intended for internal academic review and methodological refinement before journal submission.")

    heading(doc, "Abstract", 1)
    abstract = (
        "Asymptotic analysis predicts how algorithmic cost grows, but it does not capture language-runtime overhead, "
        "container representation, allocation behaviour or constants that influence observed execution time. This pilot "
        "study compared dynamic arrays, linked structures and hash tables under identical build, search, deletion and "
        "traversal workloads in Python 3.13 and optimized C++17. Experiments were executed on an Apple M2 MacBook Air "
        "with 8 GB memory and macOS 26.5.2. Four input sizes (1,000-25,000) were tested using three warm-ups and ten "
        "recorded repetitions, yielding 240 validated measurement records. At n = 25,000, median Python runtimes were "
        "1.86-91.68 times the corresponding C++ medians across the twelve structure-operation combinations. Batched "
        "search and deletion for sequential structures exhibited empirical scaling exponents of approximately "
        "1.85-2.00 because both the collection size and the number of operations increased with n; hash workloads were "
        "closer to linear. All implementations produced identical search-hit counts and post-deletion checksums. The "
        "findings support teaching Big-O together with implementation-aware measurement, while the single-machine scope, "
        "absence of Java and hardware-counter data, and submicrosecond C++ measurements make the work a pilot rather than "
        "a final general-purpose benchmark."
    )
    add_para(doc, abstract, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_rich_para(doc, [("Keywords: ", {"bold": True}), ("data structures; Big-O; empirical algorithmics; Python; C++; microbenchmarking; reproducibility", {})], align=WD_ALIGN_PARAGRAPH.LEFT)

    heading(doc, "1. Introduction", 1)
    add_para(doc, "Big-O notation provides a machine-independent description of growth as input size increases. It is indispensable for algorithm design, yet it intentionally suppresses constant factors, representation costs and hardware effects [1]. Consequently, two implementations with the same asymptotic class can differ substantially in observed runtime, while a theoretically favourable structure may carry a higher construction or traversal cost for a particular workload.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_para(doc, "This distinction is especially important in undergraduate computing education. Students often learn that hash-table lookup is expected O(1), array search is O(n), and linked-list traversal is O(n), but they may not observe how language runtimes, boxed objects, allocation strategies and contiguous memory influence actual measurements. Computer architecture texts likewise emphasise that locality and the memory hierarchy shape performance beyond instruction counts [2].", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_para(doc, "The objective of this pilot is not to declare one programming language universally superior. It is to test whether a small, reproducible experiment can connect theoretical complexity with measured behaviour while making its assumptions and limitations explicit. The resulting protocol is intended as a foundation for a student research project and a later multi-platform study.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "1.1 Research questions", 2)
    bullet(doc, "RQ1: How do language and data-structure implementation affect observed runtime for equivalent workloads?")
    bullet(doc, "RQ2: Do measured scaling patterns agree with the workload-level complexity predicted from Big-O analysis?")
    bullet(doc, "RQ3: Which methodological limitations must be addressed before extending the pilot into a journal-ready benchmark?")

    heading(doc, "1.2 Contributions", 2)
    bullet(doc, "A common, deterministic dataset and workload definition shared by Python and C++ implementations.")
    bullet(doc, "A reproducible execution pipeline with correctness checks, raw-data hashing and environment metadata.")
    bullet(doc, "An empirical distinction between per-operation complexity and the complexity of a batch whose operation count also grows with n.")
    bullet(doc, "A transparent account of measurement-resolution, implementation-equivalence and external-validity limitations.")

    heading(doc, "2. Background and Related Work", 1)
    add_para(doc, "The analysis of algorithms separates growth rate from implementation detail [1]. Experimental algorithmics complements that abstraction by examining implementations on specified workloads and machines. Algorithm engineering has been described as a methodology connecting design, implementation, experimentation and refinement [3]. This perspective motivates reporting sufficient detail to reproduce not only the code but also the experimental conditions.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_para(doc, "Performance measurement is vulnerable to effects that are easy to overlook. Mytkowicz et al. showed that apparently harmless environmental changes can alter conclusions [4]. Georges et al. and Kalibera and Jones argued for warm-ups, repeated measurements, uncertainty reporting and explicit treatment of runtime-system variability [5,6]. Fleming and Wallace further cautioned that benchmark summaries can mislead when inappropriate averages are used [7]. The present pilot therefore prioritises medians, dispersion, warm-ups, immutable raw results and correctness checks.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_para(doc, "The study is deliberately modest. It does not claim that its three containers exhaust data-structure design or that Python and C++ expose equivalent internal representations. Instead, it investigates idiomatic implementations under a shared external workload. That decision improves classroom relevance but weakens causal attribution: measured differences reflect the combined effect of language, runtime, library implementation and element representation.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "3. Materials and Methods", 1)
    heading(doc, "3.1 Execution environment", 2)
    env_rows = [
        ["Computer", "MacBook Air (Mac14,2)"],
        ["Processor", "Apple M2, 8 cores (4 performance, 4 efficiency), arm64"],
        ["Memory", "8 GB unified memory"],
        ["Operating system", "macOS 26.5.2, Darwin 25.5.0"],
        ["Python", "CPython 3.13.5"],
        ["C++", "C++17 compiled with Apple Clang 21.0.0 using -O2"],
        ["Java", "Not executed: no working JDK was available"],
        ["Hardware counters", "Not collected: Linux perf unavailable on macOS"],
        ["Execution date", "23 August 2026"],
    ]
    add_table(doc, "Table 1. Recorded execution environment.", ["Item", "Recorded value"], env_rows, [2400, 6960], 9.4)

    heading(doc, "3.2 Structures and workload", 2)
    add_para(doc, "The experiment used three abstract structures. The dynamic-array condition used Python list and C++ std::vector<int>; the linked condition used a custom Python singly linked list and C++ std::list<int>; and the hash condition used Python dict and C++ std::unordered_map<int,int>. Inputs contained unique integers in a deterministic shuffled order.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    method_rows = [
        ["Input size", "1,000; 5,000; 10,000; 25,000"],
        ["Build", "Construct the structure from all n values"],
        ["Search", "Query max(10, 0.01n) keys; half present and half absent"],
        ["Delete", "Delete max(1, 0.01n) keys known to be present"],
        ["Traverse", "Sum all keys remaining after deletion"],
        ["Correctness", "Compare search-hit count and post-deletion checksum"],
        ["Timing boundary", "Exclude dataset parsing and CSV output"],
    ]
    add_table(doc, "Table 2. Common experimental workload.", ["Component", "Definition"], method_rows, [2300, 7060], 9.4)

    heading(doc, "3.3 Dataset generation and validation", 2)
    add_para(doc, "A fixed seed (20260823) generated one text dataset per input size. Every language read the same files. A manifest stored each file's SHA-256 digest. Before performance analysis, all result groups were checked for identical search-hit counts and identical post-deletion checksums. Any disagreement would have invalidated the performance data; none occurred.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "3.4 Measurement protocol", 2)
    add_para(doc, "For every language-structure-size combination, the program performed three unrecorded warm-ups followed by ten recorded repetitions. Jobs were shuffled with the experiment seed. Operation durations were measured using monotonic high-resolution clocks and reported in nanoseconds. The complete design produced 2 languages x 3 structures x 4 sizes x 10 repetitions = 240 records.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_note(doc, "Measurement caveat", "Some optimized C++ workloads completed in less than one microsecond, and the C++ hash-search median at n = 1,000 was recorded as zero. Such values are below a dependable single-shot timing range and are treated as resolution-limited rather than literal zero-cost operations.", risk=True)

    heading(doc, "3.5 Analysis", 2)
    add_para(doc, "The primary summary was the median across ten repetitions, with the mean, standard deviation and non-parametric bootstrap interval retained in the generated analysis file. Coefficient of variation (CV) was used to describe group dispersion. Python-to-C++ median ratios at n = 25,000 were calculated descriptively; Cliff's delta was also computed. Scaling exponents between n = 5,000 and n = 25,000 were estimated as log(T2/T1) / log(n2/n1). No causal language claim is made because language and container representation were not independently manipulated.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "4. Results", 1)
    heading(doc, "4.1 Correctness and measurement stability", 2)
    add_para(doc, f"All 240 records passed the hit-count and checksum validation. The median CV across the 96 language-structure-size-operation groups was {METRICS['median_group_cv']*100:.1f}%. The maximum CV was {METRICS['max_group_cv']*100:.1f}% and occurred in the resolution-limited C++ hash-search group at n = 1,000. The data therefore show generally stable repeated measurements while also identifying the exact region in which the timer cannot support strong absolute claims.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "4.2 Search scaling", 2)
    add_picture(doc, GENERATED / "figure_1_search_scaling.png", "Figure 1. Median search-workload time across input sizes. The zero C++ hash-search median at n = 1,000 is omitted from the logarithmic plot.", "Two-panel log-log line chart comparing array, linked and hash search workload times for C++17 and Python 3.13 across four input sizes.")
    add_para(doc, "Sequential search rose much more sharply than hash search. Between 5,000 and 25,000 elements, the estimated search exponent was 1.99 for the C++ array and 2.00 for the Python array; the linked implementations produced 1.91 and 1.99, respectively. The corresponding hash exponents were 0.90 for C++ and 0.97 for Python. This apparent quadratic-versus-linear contrast is consistent with the workload definition: the number of search queries itself increases in proportion to n, so an O(n) sequential search repeated O(n) times yields an O(n^2) batch, whereas expected O(1) hash lookup repeated O(n) times yields an O(n) batch.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "4.3 Runtime at the largest input", 2)
    result_rows = []
    for structure in ("array", "linked", "hash"):
        for operation in ("insert", "search", "delete", "traverse"):
            entry = METRICS["n25000"][structure][operation]
            result_rows.append([
                structure.title(), operation.title(), fmt_ms(entry["cpp"]["median_ms"]),
                fmt_ms(entry["python"]["median_ms"]), f"{entry['python_to_cpp_median_ratio']:.2f}x",
            ])
    add_table(doc, "Table 3. Median workload runtime at n = 25,000 (ten repetitions).", ["Structure", "Operation", "C++17", "Python 3.13", "Python/C++"], result_rows, [1700, 1800, 1900, 2100, 1860], 8.8)
    ratio_min, ratio_max = METRICS["language_ratio_range_n25000"]
    add_para(doc, f"At n = 25,000, every Python median exceeded its corresponding C++ median; the descriptive ratios ranged from {ratio_min:.2f}x for hash deletion to {ratio_max:.2f}x for array traversal. Cliff's delta was 1.00 for all twelve comparisons, meaning every recorded Python duration in each comparison exceeded every corresponding C++ duration. These values characterise the tested implementations on this Mac and must not be interpreted as universal language speed factors.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_picture(doc, GENERATED / "figure_2_language_ratios.png", "Figure 2. Python-to-C++ median runtime ratios at n = 25,000. The horizontal axis is logarithmic.", "Horizontal bar chart of Python-to-C++ median runtime ratios for insertion, search, deletion and traversal across array, linked and hash structures.")

    heading(doc, "4.4 Deletion and traversal patterns", 2)
    add_para(doc, "Array and linked deletion workloads also approached quadratic scaling because 1% of n keys were deleted and each deletion required sequential location; estimated exponents ranged from 1.85 to 1.89 for linked deletion and 1.87 to 1.89 for array deletion. Hash deletion remained close to linear at 1.00 in C++ and 1.02 in Python. Traversal generally approached linear growth, with exponents between 0.84 and 0.97 across the structures and languages. These patterns are more defensible than the smallest absolute timings because they rely on changes across larger workloads.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "5. Discussion", 1)
    heading(doc, "5.1 Big-O explained, not contradicted", 2)
    add_para(doc, "The results do not show a failure of asymptotic analysis. Instead, they demonstrate why the unit of analysis must be stated carefully. A single sequential search is O(n), but this experiment schedules 0.01n searches, creating an O(n^2) batch. A hash lookup is expected O(1) on average, and the corresponding O(n) batch grew close to linearly. The empirical exponents therefore connect measured behaviour to the composed workload rather than replacing theory.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "5.2 Language and representation effects", 2)
    add_para(doc, "The Python/C++ differences include many inseparable factors: interpretation versus optimized native code, boxed Python integers versus C++ primitive integers, object allocation, iterator implementation and library design. The largest ratio occurred for contiguous traversal, where optimized native loops can exploit compact primitive storage and compiler transformations. Hash insertion and deletion showed smaller ratios, indicating that language overhead is not a single constant applied uniformly to every structure and operation.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "5.3 Educational value", 2)
    add_para(doc, "A useful teaching sequence is therefore: predict complexity, define the entire workload, implement correctness checks, measure, and then explain both agreement and disagreement. Students should learn to ask not only 'What is the Big-O?' but also 'What exactly is repeated, what representation is used, what is inside the timed region, and is the measurement long enough for the clock?' The repository makes those questions visible and reproducible.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "6. Threats to Validity", 1)
    heading(doc, "6.1 Internal validity", 2)
    add_para(doc, "Background activity, thermal conditions and operating-system scheduling were not instrumented. Although jobs were shuffled and measurements were repeated, the study did not pin processes to performance cores. Extremely short C++ operations are vulnerable to timer quantisation and clock-call overhead. A revised benchmark should batch pure operations until each timed interval exceeds a predefined duration and should separately quantify timing overhead.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "6.2 Construct validity", 2)
    add_para(doc, "The structures are functionally comparable but not internally identical. Python's custom singly linked list differs from C++ std::list, which is typically doubly linked. Python list holds object references, whereas std::vector<int> stores primitive integers contiguously. Consequently, the experiment evaluates idiomatic implementation conditions rather than isolating a pure language effect. Peak memory and cache behaviour were proposed in the broader project but were not measured on this Mac and are not inferred in this paper.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "6.3 External and conclusion validity", 2)
    add_para(doc, "One Apple M2 laptop, one Python version and one C++ toolchain cannot represent other processors, operating systems, compilers or runtime configurations. Only four sizes and one random-input family were examined. Ten repetitions support descriptive stability but not broad population inference. Java was not executed because no working JDK was available. The conclusions are therefore restricted to this environment and protocol.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "7. Conclusion and Future Work", 1)
    add_para(doc, "This reproducible Mac pilot showed that theoretical growth and observed runtime can be taught together. Sequential search and deletion batches grew close to quadratically when both collection size and operation count increased, while hash batches grew close to linearly. Python and C++ showed substantial but operation-dependent runtime differences, and all correctness outputs agreed. The study also exposed a measurement weakness: several optimized C++ workloads were too short for reliable single-shot timing.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_para(doc, "Before journal submission, the benchmark should use calibrated operation batching, add Java 17, collect peak resident memory and hardware cache counters on a controlled Linux machine, record temperature and power mode, test additional input distributions, and reproduce the experiment on at least one independent system. Those extensions should be reported as new evidence, not combined silently with the present Mac data.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "Data and Code Availability", 1)
    add_para(doc, f"The repository contains the dataset generator, Python and C++ implementations, Java source, validation tests, execution configuration, raw CSV records and analysis scripts. The raw combined CSV contains {METRICS['record_count']} records and has SHA-256 digest {METRICS['raw_sha256']}. A public repository URL and archived release identifier must be inserted before submission.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "Ethics, Authorship and AI-Assistance Statement", 1)
    add_para(doc, "No human-participant, personal or sensitive data were used. Codex assisted with repository scaffolding, code review, execution orchestration, analysis scripting and preparation of this draft. All numerical claims in the manuscript were generated programmatically from the preserved raw CSV; missing measurements were not fabricated. Before submission, the named authors must independently verify the code, results, citations and wording, approve authorship contributions, and adapt this disclosure to the selected journal's policy.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    heading(doc, "References", 1)
    references = [
        "Cormen, T. H., Leiserson, C. E., Rivest, R. L., and Stein, C. (2022). Introduction to Algorithms (4th ed.). MIT Press.",
        "Hennessy, J. L., and Patterson, D. A. (2019). Computer Architecture: A Quantitative Approach (6th ed.). Morgan Kaufmann.",
        "Sanders, P. (2009). Algorithm Engineering - An Attempt at a Definition. In Efficient Algorithms, LNCS 5760, 321-340. https://doi.org/10.1007/978-3-642-03456-5_22",
        "Mytkowicz, T., Diwan, A., Hauswirth, M., and Sweeney, P. F. (2009). Producing wrong data without doing anything obviously wrong! Proceedings of ASPLOS XIV, 265-276. https://doi.org/10.1145/1508244.1508275",
        "Georges, A., Buytaert, D., and Eeckhout, L. (2007). Statistically rigorous Java performance evaluation. Proceedings of OOPSLA 2007, 57-76. https://doi.org/10.1145/1297027.1297033",
        "Kalibera, T., and Jones, R. (2013). Rigorous benchmarking in reasonable time. Proceedings of ISMM 2013, 63-74. https://doi.org/10.1145/2464157.2464160",
        "Fleming, P. J., and Wallace, J. J. (1986). How not to lie with statistics: the correct way to summarize benchmark results. Communications of the ACM, 29(3), 218-221. https://doi.org/10.1145/5666.5673",
        "Efron, B., and Tibshirani, R. J. (1993). An Introduction to the Bootstrap. Chapman and Hall/CRC.",
        "Python Software Foundation. (2026). Python 3.13 documentation: Data structures. https://docs.python.org/3.13/tutorial/datastructures.html",
        "ISO/IEC. (2020). ISO/IEC 14882:2020 Programming Languages - C++. International Organization for Standardization.",
    ]
    for reference in references:
        p = doc.add_paragraph(style="List Number")
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.15
        set_run(p.add_run(reference), size=9.5)

    heading(doc, "Appendix A. Reproducibility Record", 1)
    appendix_rows = [
        ["Experiment configuration", "config/experiment.json"],
        ["Dataset manifest", "data/generated/manifest.json"],
        ["Raw measurements", "results/raw/combined.csv"],
        ["Environment metadata", "results/raw/environment.json"],
        ["Paper analysis", "paper/analyse_for_paper.py"],
        ["Correctness tests", "tests/test_benchmark.py; tests/test_dataset_manifest.py"],
    ]
    add_table(doc, "Table A1. Repository evidence map.", ["Evidence", "Repository path"], appendix_rows, [3000, 6360], 9.4)
    doc.core_properties.title = "Beyond Big-O: Apple-Silicon Runtime Pilot Study"
    doc.core_properties.subject = "Reproducible empirical comparison of data-structure runtime in Python and C++"
    doc.core_properties.author = "Mahesh Patil and Student Research Team"
    doc.core_properties.keywords = "Big-O, data structures, runtime, Python, C++, Apple M2, reproducibility"
    doc.core_properties.comments = "Draft generated from executed Mac measurements; requires author and journal-specific review."
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
