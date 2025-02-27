#!/usr/bin/env python3
# This file is part of the GAMM_PDFs_FROM_CONFTOOL project.
# Copyright GAMM_PDFs_FROM_CONFTOOL developers and contributors. All rights reserved.
# License: BSD 2-Clause License (https://opensource.org/licenses/BSD-2-Clause)

import datetime as dt
import pandas as pd
import re
import argparse

from html2latex import html2latex

################################################################################
# cleaner routine that handles all characters giving plain pdflatex trouble    #
################################################################################
def utf8_clean(instr):
    utf8_to_latex = {
    " &": " \&",
    "#": "\\#",
    "Γ": "\\ensuremath\\Gamma ",
    "Ω": "\\ensuremath\\Omega ",
    "∑": "\\ensuremath\\Sigma ",
    "∇": "\\ensuremath\\nabla ",
    "Δ": "\\ensuremath\\Delta ",
    "√": "\\ensuremath\\sqrt",
    "⋆": "\\ensuremath\\ast ",
    "λ": "\\ensuremath\\lambda ",
    "φ": "\\ensuremath\\varphi ",
    "ε": "\\ensuremath\\varepsilon ",
    "ϕ": "\\ensuremath\\Phi ",
    "∈": "\\ensuremath\\in ",
    "ψ": "\\ensuremath\\psi ",
    "ξ": "\\ensuremath\\xi ",
    "π": "\\ensuremath\\pi ",
    "μ": "\\ensuremath\\mu ",
    "∞": "\\ensuremath\\infty ",
    "β": "\\ensuremath\\beta ",
    "ω": "\\ensuremath\\omega ",
    "→": "\\ensuremath\\rightarrow ",
    "\u03c3": "\\ensuremath\\sigma ",
    "θ": "\\ensuremath\\Theta ",
    "\R": "\\mathbb{R}",
    "≤": "\\ensuremath\\leq",
    "\u2003": "~",
    "\u202F": "~",
    "\u2248": "",
    "\u2212": "-",
    "\u0308": '\\"',
    "\u0301": "\\\'",
    "\u001B": "",
    "^2": "\\textsuperscript{2}",
    "^m": "\\textsuperscript{m}",
    "\percent": "\%", # we replaced % by \percent in html2latex
    "\&=": "&=" 
    }

    for key, value in utf8_to_latex.items():
        instr = instr.replace(key, value)
    return instr

################################################################################
# for the daily schedule we need to know how long a contribution is,           #
# and advance time by 20 minutes                                               #
################################################################################
def get_duration(start, end):
    dt1 = dt.datetime.fromisoformat(start)
    dt2 = dt.datetime.fromisoformat(end)
    return (dt2-dt1).total_seconds() / 60

def advance_slot(start, times, slot=20):
    match slot:
        case 20:
            delta = dt.timedelta(seconds=times*1200)
        case 30:
            delta = dt.timedelta(seconds=times*1800)
    return start + delta

################################################################################
# helper routines fetching row entries from the CSV dataframe into easier to   #
# handle dictioniaries                                                         #
################################################################################
def get_section_info(df, section):
    if section.startswith('DFG-PP'):
        section = section.replace('DFG-PP', 'SPP')
    if section.startswith('DFG-GRK'):
        section = section.replace('DFG-GRK', 'GRK')
    sect_organ = df[df['track_type'].str.startswith(section)]
    organizers = ''
    title = '\\color{red}{NOT AVAILABLE}'
    first = True
    for _, row in sect_organ.iterrows():
        if not first:
            organizers += '\\newline '
        organizers += f'{row["name"]}, {row["firstname"]} {{\\em ({row["organisation"]})}}'
        title = row["track_type"]
        first = False
    return title, organizers

def get_session_info(row):
    start = dt.datetime.fromisoformat(row['session_start'])
    end   = dt.datetime.fromisoformat(row['session_end'])
    c1 = row['chair1']
    c2 = row['chair2']
    c3 = row['chair3']

    if pd.isna(c3):
        if pd.isna(c2):
            if pd.isna(c1):
                chairs = ''
            else:
                chairs = c1
        else:
            chairs = f'{c1}\\newline {c2}'
    else:
        chairs = f'{c1}\\newline {c2}\\newline {c3}'

    session = {
        "chairs"   : chairs,
        "number"   : row['session_short'],
        "name"     : row['session_title'],
        "room"     : row['session_room'],
        "start"    : start.strftime("%H:%M"),
        "end"      : end.strftime("%H:%M"),
        "date"     : start.strftime("%B %d, %Y")
    }
    return session

def get_contribution_info(row, idx, RvML=False):
    ptitle     = f'p{idx}_title'
    pauthors   = f'p{idx}_authors'
    porgas     = f'p{idx}_organisations'
    ppresenter = f'p{idx}_presenting_author'
    pabstract  = f'p{idx}_abstract'
    pstart     = f'p{idx}_start'
    pend       = f'p{idx}_end'

    presenter = row[ppresenter]
    if pd.isna(presenter):
        return None
    authors = row[pauthors]
    authors = authors.replace(presenter, f'\\presenter{{{presenter}}}')
    if row['session_short'].startswith('Poster'):
        duration = 0
    else:
        duration = get_duration(row[pstart], row[pend])
    if row[pabstract] != row[pabstract]:
        abstract = ''
    else:
        abstract = html2latex(row[pabstract])
    if RvML:
        start = dt.datetime.fromisoformat(row[pstart]).strftime('%H:%M')
        end   = dt.datetime.fromisoformat(row[pend]).strftime('%H:%M')
    else:
        start = row[pstart]
        end   = row[pend]
    
    contribution = {
        "title"         : row[ptitle],
        "authors"       : authors,
        "presenter"     : presenter,
        "start"         : start,
        "end"           : end,
        "duration"      : duration,
        "abstract"      : abstract,
        "organizations" : row[porgas]
    }
    return contribution

def get_plenary_info(row):
    start = dt.datetime.fromisoformat(row['session_start'])
    end   = dt.datetime.fromisoformat(row['session_end'])
    if pd.isna(row['chair1']):
        chair = '\color{red} NOT AVAILABLE'
    else:
        chair = row['chair1']
    if pd.isna(row['p1_organisations']):
        speaker = '\presenter{' + row['p1_presenting_author'] + '}'
    else:
        speaker = '\presenter{' + row['p1_presenting_author'] + '} {\\em (' + row['p1_organisations'] + ')}'
    contribution = {
        "session"  : row['session_short'],
        "title"    : row['p1_title'],
        "speaker"  : speaker,
        "abstract" : html2latex(row['p1_abstract']),
        "chair"    : chair,
        "room"     : row['session_room'],
        "start"    : start.strftime("%H:%M"),
        "end"      : end.strftime("%H:%M"),
        "date"     : start.strftime("%B %d, %Y")
    }
    return contribution

################################################################################
# helpers for writing the actual section files in LaTeX                        #
################################################################################
def write_PML(df, outdir):
    file = open(outdir+'/PML.tex', 'w', encoding='utf-8')
    for _, row in df.iterrows():
        PML = get_plenary_info(row)
        ostring  = f'\\Prandtl{{{PML["title"]}}}%\n'
        ostring += f'        {{{PML["session"]}}}%\n'
        ostring += f'        {{{PML["speaker"]}}}%\n'
        ostring += f'        {{{PML["date"]}}}%\n'
        ostring += f'        {{{PML["start"]}}}%\n'
        ostring += f'        {{{PML["end"]}}}%\n'
        ostring += f'        {{{PML["room"]}}}%\n'
        ostring += f'        {{{PML["chair"]}}}%\n'
        ostring += f'        {{{PML["abstract"]}}}%\n'
        ostring = utf8_clean(ostring)
        file.write(ostring)
        file.close()
    return '\\input{PML.tex}\n'

def write_PL(df, outdir):
    inputs = ''
    for _, row in df.iterrows():
        PL = get_plenary_info(row)
        fname = f'{PL["session"]}.tex'
        file = open(outdir+'/'+fname, 'w', encoding='utf-8')
        ostring  = f'\\Plenary{{{PL["title"]}}}%\n'
        ostring += f'        {{{PL["session"]}}}%\n'
        ostring += f'        {{{PL["speaker"]}}}%\n'
        ostring += f'        {{{PL["date"]}}}%\n'
        ostring += f'        {{{PL["start"]}}}%\n'
        ostring += f'        {{{PL["end"]}}}%\n'
        ostring += f'        {{{PL["room"]}}}%\n'
        ostring += f'        {{{PL["chair"]}}}\n'
        ostring += f'        {{{PL["abstract"]}}}%\n'
        ostring = utf8_clean(ostring)
        file.write(ostring)
        file.close()
        inputs += f'\\input{{{fname}}}\n'
    return inputs

def write_RvML(df, outdir):
    file = open(outdir+'/RvML.tex', 'w', encoding='utf-8')
    for _, row in df.iterrows():
        date = dt.datetime.fromisoformat(row['session_start']).strftime("%B %d, %Y")
        room = row['session_room']
        ostring = ''
        for j in range(1,3):
            RvML = get_contribution_info(row,j, RvML=True)
            if not pd.isna(row[f'p{j}_presenting_author']):
                ostring += f'\\Mises{{{RvML["title"]}}}%\n'
                ostring +=  '       {Richard von Mises Lecture}%\n'
                ostring += f'       {{\\presenter{{{RvML["presenter"]}}}~{{\\em({RvML["organizations"]})}}}}%\n'
                ostring += f'       {{{date}}}%\n'
                ostring += f'       {{{RvML["start"]}}}%\n'
                ostring += f'       {{{RvML["end"]}}}%\n'
                ostring += f'       {{{room}}}{{}}%\n'
        ostring = utf8_clean(ostring)
        file.write(ostring)
        file.close()
    return '\\input{RvML.tex}\n'

def write_section(org, sec, df, outdir, toc_sessions_silent=False):
    fname = sec.replace(' ', '_')
    fullname = outdir+'/'+fname+'.tex'
    file = open(fullname, 'w', encoding='utf-8')
    title, organizers = get_section_info(org, sec)
    ostring  = f'\\Section{{{title}}}%\n'
    ostring += f'        {{{organizers}}}\n\n'

    sessions = df[df['session_short'].str.startswith(sec)]
    for _, row in sessions.iterrows():
        S = get_session_info(row)
        if toc_sessions_silent:
            ostring += '\SSession'
        else:
            ostring += '\Session'
        ostring += f'{{{S["number"]}}}%\n'
        ostring += f'{{{S["name"]}}}%\n'
        ostring += f'{{{S["date"]}}}%\n'
        ostring += f'{{{S["start"]}}}%\n'
        ostring += f'{{{S["end"]}}}%\n'
        ostring += f'{{{S["room"]}}}%\n'
        ostring += f'{{{S["chairs"]}}}%\n'
        for i in range(1,7):
            C = get_contribution_info(row, i)
            if C is None:
                break
            organizations = C["organizations"]
            organizations = organizations.replace('; ','\\newline ')
            start = re.sub('^.* ','', C["start"])
            ostring += f'\\Contribution{{{C["title"]}}}%\n'
            ostring += f'{{{C["authors"]}}}%\n'
            ostring += f'{{{start}}}%\n'
            ostring += f'{{{organizations}}}\n'
            ostring += f'{{{html2latex(C["abstract"])}}}%\n'
    ostring = utf8_clean(ostring)
    file.write(ostring)
    file.close()
    return fname

def write_sections(organizers, sessions, outdir):
    inputs = ''
    for i in range(1,27):
        if not i == 6:
            fname = write_section(organizers, f'S{i:02}', sessions, outdir)
            inputs += f'\\input{{{fname}}}\n'
        else:
            fname1 = write_section(organizers, f'S{i:02}.1', sessions, outdir)
            fname2 = write_section(organizers, f'S{i:02}.2', sessions, outdir)
            inputs += f'\\input{{{fname1}}}\n\\input{{{fname2}}}\n'
    return inputs

def write_minis(organizers, MS, YRM, outdir):
    inputs = ''
    for i in range(len(MS)):
        name = f'MS{i+1}'
        fname = write_section(organizers, name, MS, outdir,
                              toc_sessions_silent=True)
        inputs += f'\\input{{{fname}}}\n'

    for i in range(len(YRM)):
        name = f'YRM{i+1}'
        fname = write_section(organizers, name, YRM, outdir,
                              toc_sessions_silent=True)
        inputs += f'\\input{{{fname}}}\n'
    return inputs

def write_dfg(organizers, df, outdir):
    inputs = ''
    for _, row in df.iterrows():
        fname = write_section(organizers, row['session_short'], df, outdir,
                              toc_sessions_silent=True)
        inputs += f'\\input{{{fname}}}\n'
    return inputs

################################################################################
# routine for writing the tables in the daily session program                 #
################################################################################
def make_session_table(SAT, start, n, withMises=False):
    match n:
        case 1:
            inputs = '\\begin{longtable}{PA|}\n'
        case 2:
            inputs = '\\begin{longtable}{PmM|}\n'
        case 3:
            inputs = '\\begin{longtable}{Pxyx|}\n'
        case 6:
            inputs = '\\begin{longtable}{PXYXYXY|}\n'
        case 16: #this is the same magic 16 as in make_dsp working for 2024's GAMM
            inputs = '\\begin{longtable}{PA|}\n'
        case _: # non-standard session length
            raise SystemExit('non-standard session length detected')

    inputs += '    \\rowcolor{primary}'
    if n != 16:
        k = n
    else:
        k = 1 # Exception for Poster session
    for i in range(k):
        slot_start = advance_slot(start, i).strftime("%H:%M")
        inputs += f'&\\white{{{slot_start}}}'
    inputs += '\\\\\n\endhead\n'
    skip = False
    for _, row in SAT.iterrows():
        sname = row['session_short']
        sroom = row['session_room']
        inputs += f'\\white{{{sname}}}\\newline\\white{{\small ({sroom})}}'
        j = 0 # j counts speakers/contributions in the session CSV
        drop_extra_empty = False
        for i in range(n): # i counts table columns
            if not skip:
                j += 1
                contribution = get_contribution_info(row, j)
                if contribution is None:
                    if sname == 'RvML':
                        inputs += '\n&\\footnotesize{\\bfseries Price winner(s) and title(s) will be announced in the Opening}'
                    else:
                        if not drop_extra_empty:
                            inputs += '\n&'
                else:
                    match contribution["duration"]:
                        case 60: # PLenary lectures (incl Prandtl)
                            inputs += f'\n&\\footnotesize{{\\bfseries {contribution["title"]}}}\\newline\presenter{{{contribution["presenter"]}}}'
                        case 40: # Topcial Speakers
                            skip = True # found a topical speaker double slot and skip next
                            match n:
                                case 3:
                                    inputs += '\n&\multicolumn{2}{t}'
                                case 6:
                                    inputs += '\n&\multicolumn{2}{T}'
                            inputs += f'{{\\footnotesize{{\\bfseries {contribution["title"]}}}\\newline\presenter{{{contribution["presenter"]}}}}}'
                        case 30: # either von Mises Lecture session with 2 talks or Minisymposium with 4 talks
                            if sname == 'RvML':
                                if withMises:
                                    inputs += f'\n&\\footnotesize{{\\bfseries {contribution["title"]}}}\\newline\presenter{{{contribution["presenter"]}}}'
                                else:
                                   inputs += '\n&\\footnotesize{\\bfseries Price winner(s) and title(s) will be announced in the Opening}'
                            else:
                                match i:
                                    case 0:
                                        drop_extra_empty = True
                                        inputs += '\n&\multicolumn{6}{A}{\\noindent\\begin{tabularx}{\linewidth}{@{}BCBC@{}}'
                                        inputs += f'\\footnotesize{{\\bfseries {contribution["title"]}}}\\newline\presenter{{{contribution["presenter"]}}}'
                                    case 3:
                                        inputs += f'\n&\\footnotesize{{\\bfseries {contribution["title"]}}}\\newline\presenter{{{contribution["presenter"]}}}'
                                        inputs += '\end{tabularx}}'
                                    case _:
                                        inputs += f'\n&\\footnotesize{{\\bfseries {contribution["title"]}}}\\newline\presenter{{{contribution["presenter"]}}}'
                        case 20: # the default 20 minutes section talks
                            shift = get_duration(advance_slot(start,i).isoformat(), contribution["start"])
                            if shift > 0: # there is a gap in the schedule
                                inputs += '\n&' # add empty cell
                                j -= 1 # revisit contribution for next column
                            else:
                                inputs += f'\n&\\footnotesize{{\\bfseries {contribution["title"]}}}\\newline\presenter{{{contribution["presenter"]}}}'
                        case 0: # we explicitly set 0 for posters
                            inputs += f'\n&\\footnotesize{{\\bfseries {contribution["title"]}}}\\newline\presenter{{{contribution["presenter"]}}}\\\\\\hline'
            else:
                skip = False
        inputs += '\\\\\\hline\n'
    inputs += '\end{longtable}\n'
    return utf8_clean(inputs)

def make_room_session_table(row, day, withMises=False):
    start = dt.datetime.fromisoformat(row['session_start'])
    end = dt.datetime.fromisoformat(row['session_end'])
    stime = start.strftime("%H:%M")
    etime = end.strftime("%H:%M")
    inputs  = f'\n\\begin{{samepage}}\n\\section*{{{day}\hfill{stime}--{etime}}}\n'
    session = row['session_short']
    inputs += f'\n\\begin{{center}}\huge\\bfseries {session}\end{{center}}\n'
    inputs += '\\begin{tabularx}{\linewidth}{|A|B|}\n\hline\n'
    for i in range(1,7):
        contribution = get_contribution_info(row, i)
        if contribution is not None:
            if (not withMises) and (session == 'RvML'):
                if i == 1:
                    cstart = start.strftime("%H:%M")
                    inputs += f'{cstart}&\n'
                    inputs += '\\textbf{Price winner(s) and title(s) will be announced in the Opening}\\\\\hline\n'
            else:
                if contribution["duration"] == 0: # set explicitly for posters
                    cstart = start.strftime("%H:%M")
                else:
                    cstart = dt.datetime.fromisoformat(contribution["start"]).strftime("%H:%M")
                inputs += f'{cstart}&\n'
                inputs += f'\\textbf{{{contribution["title"]}}}\\newline\\textit{{{contribution["presenter"]}}}\\\\\hline\n'
        else:
            if (session == 'RvML') and (i == 1):
                cstart = start.strftime("%H:%M")
                inputs += f'{cstart}&\n'
                inputs += '\\textbf{Price winner(s) and title(s) will be announced in the Opening}\\\\\hline\n'

    inputs += '\end{tabularx}\n\end{samepage}\n'

    return utf8_clean(inputs)
################################################################################
# top-level routines for generating the book of abstracts and daily session    #
# program                                                                      #
################################################################################
def make_boa(df, withMises=False):
    # Filter by the categories desired as chapter in the BoA
    DFG              = df[df['session_short'].str.startswith('DFG')].sort_values(by='session_short')
    Prandtl          = df[df['session_short'].str.startswith('PML')].sort_values(by='session_short')
    Plenaries        = df[df['session_short'].str.startswith('PL')].sort_values(by='session_short')
    Minisymposia     = df[df['session_short'].str.startswith('MS')].sort_values(by='session_short')
    YoungResearchers = df[df['session_short'].str.startswith('YRM')].sort_values(by='session_short')
    Contributed      = df[df['session_short'].str.startswith('S')].sort_values(by='session_short')

    # Read the relevant Organizer information exported from ConfTool
    Organizers = pd.read_csv('CSV/organizers.csv',
                            sep=';',
                            quotechar='"',
                            usecols=['track_type', 'name', 'firstname', 'organisation'])
    # drop everyone whos not a session organizer and sort by sections
    Organizers = Organizers[Organizers.track_type.notnull()].sort_values(by='track_type')

    outdir  = './LaTeX/Book_of_abstracts/Sessions/'
    inputs  = '\chapter{Prandtl Memorial Lecture and Plenary~Lectures}\n'
    inputs += write_PML(Prandtl, outdir)
    inputs += write_PL(Plenaries, outdir)
    if withMises:
        vonMises = df[df['session_short'].str.startswith('RvML')].sort_values(by='session_short')
        inputs  += '\chapter{Richard von Mises Price Lecture(s)}\n'
        inputs  += write_RvML(vonMises, outdir)
    inputs += '\chapter{Minisymposia and Young~Researchers~Minisymposia}\n'
    inputs += write_minis(Organizers, Minisymposia, YoungResearchers, outdir)
    inputs += '\chapter{DFG Programs}\n'
    inputs += write_dfg(Organizers, DFG, outdir)
    inputs += '\chapter{Contributed Sessions}\n'
    inputs += write_sections(Organizers, Contributed, outdir)

    boa = open('./LaTeX/Book_of_abstracts/BookOfAbstracts.tex', 'w', encoding = 'utf-8')
    contents = '''\\documentclass[colorlinks]{gamm-boa}

\\begin{document}
\\tableofcontents
CONTENTS
\\printindex
\\end{document}
'''
    contents = contents.replace('CONTENTS', inputs)
    boa.write(contents)
    boa.close()

def make_dsp(df, withMises=False):
    df = df.sort_values(by='session_start')
    session_starts = df['session_start'].unique()

    dsp = open('./LaTeX/Daily_Scientific_Program/Daily_Scientific_Program.tex', 'w', encoding = 'utf-8')

    inputs = ''
    old_day = ''
    for session in session_starts:
        start = dt.datetime.fromisoformat(session)
        day = start.strftime("%A, %B %d")
        if old_day != day:
            old_day = day
            inputs += f'\\chapter{{{day}}}\n'
        #inputs += f'\\section*{{{start.strftime("%H:%M")}}}\n'
        SAT = df[df['session_start'] == session].sort_values(by='session_short') # session at time
        length = get_duration(session, SAT['session_end'].values[0])
        match len(SAT):
            case 1: # only one parallel session, i.e. Plenary or Poster
                if SAT['session_short'].values[0].startswith('PL') | SAT['session_short'].values[0].startswith('PML') | SAT['session_short'].values[0].startswith('RvML'):
                    inputs += make_session_table(SAT, start, int(1))
                if SAT['session_short'].values[0].startswith('Poster'):
                    inputs += make_session_table(SAT, start, int(16)) # TODO 16 seems to be the maximum for this conference. This may need fixing
                if SAT['session_short'].values[0].startswith('RvML'):
                    inputs += make_session_table(SAT, start, 2, withMises=withMises)
            case _:
                num_slots = length / 20
                inputs += make_session_table(SAT, start, int(num_slots))
    contents = '''\documentclass[colorlinks]{gamm-dsp}

\\begin{document}
\\tableofcontents
\\arrayrulecolor{primary}

CONTENTS
\printindex
\end{document}
'''
    contents = contents.replace('CONTENTS', inputs)
    dsp.write(contents)
    dsp.close()

def make_room_plans(df, withMises=False):
    outdir = './LaTeX/Daily_Scientific_Program/rooms/'
    df = df.sort_values(by='session_room')

    template_file = open('./LaTeX/Daily_Scientific_Program/room_template.tex', 'r', encoding = 'utf-8')
    template = template_file.read()
    template_file.close()

    rooms = df['session_room'].unique()
    for room in rooms:
        print(f'Generating room: {room}\n')
        sessions = df[df['session_room'] == room].sort_values(by='session_start')
        room = room.replace('/', '-')
        room_file = open(f'{outdir}{room}.tex', 'w', encoding = 'utf-8')
        old_day = ''
        inputs = ''
        for _, row in sessions.iterrows():
            day = dt.datetime.fromisoformat(row['session_start'].replace(' ','T')).strftime("%A, %B %d")
            if old_day != day:
                old_day = day
                inputs += '\n\pagebreak[4]'
            inputs += make_room_session_table(row, day, withMises=withMises)
        contents = template.replace('ROOM', room)
        contents = contents.replace('CONTENTS', inputs)
        room_file.write(contents)


################################################################################
# Main function                                                                #
################################################################################
def main():
    parser = argparse.ArgumentParser(description='Generate PDFs for conference materials.')
    parser.add_argument('-m', '--withMises', action='store_true', help='onclude von Mises lecturer(s) and title(s)')
    args = parser.parse_args()

    if args.withMises:
        withMises = True
    else:
        withMises = False

    print(f'\nInclude von Mises Prize lectures: {withMises}\n\n')

    # Read the Sessions exported from ConfTool
    df = pd.read_csv('CSV/sessions.csv', sep=';', quotechar='"')

    print('\nGenerating book of abstracts LaTeX files\n')
    make_boa(df, withMises=withMises)
    print('\nGenerating Session Table LaTeX files\n')
    make_dsp(df, withMises=withMises)
    print('\nGenerating Room Plan LaTeX files\n')
    make_room_plans(df, withMises=withMises)

if __name__ == "__main__":
    main()
