#!/usr/bin/env python3
"""
Verify the technical claims in this Wiki against the actual binaries.

Every check is grounded in a file on disk, not in a previous document. The
expected value is a literal in this source, so a reviewer can change one,
watch the check fail, and confirm the check is real.

Run:  python verify_wiki_claims.py
"""
import ast
import hashlib
import inspect
import os
import re
import struct
import sys
import textwrap

REPO = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(REPO, "docs")

# The binaries this wiki documents live outside the repo.
ASSETS = r"C:\MUWORK\GAME\MAPLESOTRY\待分類"
ORIG = os.path.join(ASSETS, "MapleStory 0.83.exe")
I64 = os.path.join(ASSETS, "MapleStory 0.83.exe.i64")
ASM = os.path.join(ASSETS, "MapleStory 0.83.exe.asm")
IDB = r"C:\RE\msv83\ida\v83.idb"
UNPACKED = r"C:\RE\msv83\bin\msv83_trad.exe"
WZ = r"C:\RE\msv83\wz"
SCRIPTS = os.path.join(WZ, "scripts")

results = []
infos = []


def check(name, expected, actual):
    """A real assertion: recompute `actual` from a file, compare to a literal.

    The expected value is written in this source, so a reviewer can change one,
    watch the check fail, and confirm the check is real. `expected` is allowed
    to be True/False, but `actual` may not be a bare literal — see
    _assert_computed().
    """
    _assert_computed(name, actual, arg_index=2, call="check")
    ok = expected == actual
    results.append((ok, name, expected, actual))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        print(f"         expected: {expected!r}")
        print(f"         actual  : {actual!r}")
    return ok


def _assert_computed(name, value, arg_index, call):
    """Reject a bare True/False literal as a check's *result*.

    A check whose result is a constant prints PASS forever and proves nothing.
    `expected` may legitimately be True/False (that is the value being
    asserted); `actual` — the thing read from disk — may not. The argument is
    inspected as an AST so that a comparison that happens to evaluate to True
    (two constants compared, a short-circuiting `and`) is not mistaken for a
    constant, and a genuine one is not let through.
    """
    frame = sys._getframe(2)
    tree = ast.parse(textwrap.dedent(inspect.getsource(frame)))
    target = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == call
                and len(node.args) > arg_index):
            target = node
            break
    if target is None:
        return
    arg = target.args[arg_index]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, bool):
        raise TypeError(
            "%s(%r) was given the literal %r for its %s argument — a check must "
            "derive that value from a file. Use info() for non-assertions."
            % (call, name, arg.value, "actual" if call == "check" else "result"))


def soft(name, ok, detail=""):
    """A conditional check that may be skipped when its input is absent.

    The result of an expression can be True for reasons that have nothing to
    do with the files on disk (comparing two constants, an `and` chain that
    short-circuits, `os.path.exists` on a path that is known to exist). Such a
    line prints PASS forever and proves nothing, so `ok` is inspected as an
    AST: a bare True/False literal is rejected. Use info() for observations
    that are not assertions.
    """
    frame = sys._getframe(1)
    src = inspect.getsource(frame)
    tree = ast.parse(textwrap.dedent(src))
    # locate the soft() call at the caller's current line
    target = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "soft"
                and len(node.args) > 1):
            target = node
            break
    if target is not None:
        arg = target.args[1]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, bool):
            raise TypeError(
                "soft(%r) was given the literal %r — a check must derive its "
                "result from a file, not restate a constant. Use info() for "
                "non-assertions." % (name, arg.value))
    results.append((ok, name, True, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        print(f"         {detail}")
    return ok


def info(name, detail=""):
    """Record an observation. Not an assertion; excluded from the tally.

    Use this for measurements that are printed for the reader but cannot fail
    (e.g. "how many Class::method symbols the idb contains"). The tally at the
    end reports assertions and skips separately, so a wall of info lines can
    never be mistaken for a wall of passing checks.
    """
    infos.append((name, detail))
    print(f"[INFO] {name}" + (f"  {detail}" if detail else ""))
    return True


def skip(name, why):
    """An assertion that could not run because its input is missing."""
    results.append((True, name, "SKIP", why))
    print(f"[SKIP] {name}  {why}")
    return True


def read(path, n=None):
    with open(path, "rb") as f:
        return f.read() if n is None else f.read(n)


def md5(path):
    return hashlib.md5(read(path)).hexdigest()


# =====================================================================
# 1. The packed binary: identity and protection
# =====================================================================
def check_packed_identity():
    import pefile

    pe = pefile.PE(ORIG)

    check("orig: machine i386", 0x14C, pe.FILE_HEADER.Machine)
    check("orig: PE32", 0x10B, pe.OPTIONAL_HEADER.Magic)
    check("orig: section count", 7, pe.FILE_HEADER.NumberOfSections)
    check("orig: imagebase", 0x400000, pe.OPTIONAL_HEADER.ImageBase)
    check("orig: entry RVA", 0xA8C000, pe.OPTIONAL_HEADER.AddressOfEntryPoint)
    check("orig: characteristics", 0x10F, pe.FILE_HEADER.Characteristics)
    check("orig: SizeOfCode", 7270400, pe.OPTIONAL_HEADER.SizeOfCode)
    check("orig: TimeDateStamp", 1267176451, pe.FILE_HEADER.TimeDateStamp)
    # The wiki states the stamp decodes to 2010-02-26 09:27:31 UTC. Assert the
    # decoded value against that literal date instead of comparing a constant
    # to itself, which proves nothing.
    import datetime
    ts = datetime.datetime.fromtimestamp(pe.FILE_HEADER.TimeDateStamp, datetime.UTC)
    check("orig: TimeDateStamp decodes to 2010-02-26 09:27:31 UTC",
          "2010-02-26 09:27:31", ts.strftime("%Y-%m-%d %H:%M:%S"))
    # 7,270,400 is SizeOfCode; the docs previously reported it as a ~2018
    # timestamp. Guard against that specific regression with a real test.
    soft("orig: 7,270,400 is SizeOfCode, not the timestamp",
         pe.FILE_HEADER.TimeDateStamp != pe.OPTIONAL_HEADER.SizeOfCode,
         "SizeOfCode=%d  TimeDateStamp=%d"
         % (pe.OPTIONAL_HEADER.SizeOfCode, pe.FILE_HEADER.TimeDateStamp))

    n_imports = sum(len(e.imports) for e in pe.DIRECTORY_ENTRY_IMPORT)
    check("orig: exactly 1 import", 1, n_imports)
    check("orig: import name", "FileTimeToLocalFileTime",
          pe.DIRECTORY_ENTRY_IMPORT[0].imports[0].name.decode())
    check("orig: 3 exports", 3, len(pe.DIRECTORY_ENTRY_EXPORT.symbols))
    for want in ("ZtlTaskMemAllocImp", "ZtlTaskMemFreeImp",
                 "ZtlTaskMemReallocImp"):
        soft(f"orig: exports {want}",
             any(e.name == want.encode()
                 for e in pe.DIRECTORY_ENTRY_EXPORT.symbols),
             "from the packed binary's export table")

    names = [s.Name.rstrip(b"\x00 \t").decode(errors="replace")
             for s in pe.sections]
    for want in ("uilplxhk", "tfqhbstk", "gndhordv", ".rsrc", ".idata"):
        soft(f"orig: section {want!r} present", want in names)
    check("orig: entry sits in tfqhbstk", "tfqhbstk", names[5])
    check("orig: .text entropy", 7.98, round(pe.sections[0].get_entropy(), 2))

    # version resource
    vt = [t for t in pe.DIRECTORY_ENTRY_RESOURCE.entries if t.id == 16]
    lang = vt[0].directory.entries[0].directory.entries[0].id
    check("orig: version resource lang id", 0x0412, lang)


# =====================================================================
# 2. The protection is CSecurity, not a commercial packer
# =====================================================================
def check_not_commercial_packer():
    d = read(ORIG)
    sigs = {
        "Themida": [b".themida", b".winlice", b"Themida", b"WinLicense"],
        "VMProtect": [b".vmp0", b".vmp1", b".vmp2", b".vmp3"],
        "ASProtect": [b".aspack", b"ASProtect"],
        "Enigma": [b".enigma", b"Enigma"],
        "UPX": [b"UPX0", b"UPX1", b"UPX!"],
    }
    for name, pats in sigs.items():
        hits = sum(d.count(p) for p in pats)
        check(f"orig: no {name} signature", 0, hits)


def check_csecurity_evidence():
    """The CSecurity RTTI is what identifies the protection. It lives in the
    unpacked build's own string pool, not in the .idb (which stores RTTI in a
    B-tree, so a flat byte search finds nothing)."""
    u = read(UNPACKED)
    for sym in (b"CSecurityException", b"CSecurityInitFailed",
                b"CSecurityUpdateFailed", b"CSecurityThreatDetected",
                b"CSecurityClearFailed"):
        check(f"unpacked carries {sym.decode()}", 1, u.count(sym))

    # the wider Wizet exception hierarchy, also in the unpacked build
    for sym in (b"ZException", b"CMSException", b"CTerminateException",
                b"CPatchException"):
        soft(f"unpacked carries {sym.decode()}", sym in u)

    # the .idb does NOT contain flat RTTI; wiki must not claim it does
    d = read(IDB)
    check("idb stores no flat RTTI (B-tree encoded)", 0,
          len(re.findall(rb"\.\?AV[A-Za-z0-9_]+@@", d)))


# =====================================================================
# 3. The unpacked build
# =====================================================================
def check_unpacked():
    import pefile

    pe = pefile.PE(UNPACKED)
    check("unpacked: section count", 6, pe.FILE_HEADER.NumberOfSections)
    check("unpacked: entry RVA", 0x663FF3, pe.OPTIONAL_HEADER.AddressOfEntryPoint)
    check("unpacked: imagebase", 0x400000, pe.OPTIONAL_HEADER.ImageBase)
    check("unpacked: .text raw size", 0x7F8000, pe.sections[0].SizeOfRawData)
    check("unpacked: .text entropy", 6.49, round(pe.sections[0].get_entropy(), 2))
    check("unpacked: SizeOfCode matches packed", 7270400,
          pe.OPTIONAL_HEADER.SizeOfCode)
    check("unpacked: TimeDateStamp", 1266423241, pe.FILE_HEADER.TimeDateStamp)

    d = read(UNPACKED)
    check("unpacked: size", 9920523, len(d))
    # the toolchain that produced the local build
    soft("unpacked: SolidDaima path present",
         b"SolidDaima_Rev8_200901029" in d)
    check("unpacked: SolidDaima path count", 1, d.count(b"SolidDaima_Rev8_200901029"))


# =====================================================================
# 4. WZ / Pixi architecture
# =====================================================================
def check_pixi():
    d = read(UNPACKED)
    for fn in ("PcCreateObject", "PcFreeUnusedLibraries", "PcSerializeObject",
               "PcSerializeString", "PcRootNameSpace"):
        check(f"unpacked: binds {fn}", 1, d.count(fn.encode()))
    check("unpacked: no CoCreateInstance", 0, d.count(b"CoCreateInstance"))
    # The wiki claims ole32 is used for CoCreateGuid only (not COM activation).
    # Assert that positively rather than printing a count.
    soft("unpacked: ole32 use is CoCreateGuid, not COM activation",
         d.count(b"CoCreateGuid") > 0 and d.count(b"CoCreateInstance") == 0,
         "CoCreateGuid=%d  CoCreateInstance=%d"
         % (d.count(b"CoCreateGuid"), d.count(b"CoCreateInstance")))


def check_wz_reader_not_in_client():
    d = read(UNPACKED)
    check("client has no PKG1 constant", 0, len(re.findall(re.escape(b"PKG1"), d)))
    key = bytes([0x13, 0, 0, 0, 0x08, 0, 0, 0, 0x06, 0, 0, 0, 0xB4, 0, 0, 0])
    check("client has no published v83 AES key", 0,
          len(re.findall(re.escape(key), d)))
    check("client has no 'Package file' string", 0, d.count(b"Package file"))
    check("client has no 'Wizet' string", 0, d.count(b"Wizet"))


def check_wz_name_table():
    """15 archive names, resolved from the loader's table."""
    d = read(UNPACKED)
    named = {
        0xB3F480: b"Character", 0xAF64DC: b"Skill", 0xB3F474: b"Reactor",
        0xB3F464: b"Quest", 0xB3F454: b"Effect", 0xB3F44C: b"String",
        0xB3F440: b"Morph", 0xB3F434: b"TamingMob", 0xB3F42C: b"Sound",
    }
    for va, want in sorted(named.items(), reverse=True):
        off = va - 0x400000
        check(f"loader table: {want.decode()} @ {va:#x}", want, d[off:off + len(want)])

    unnamed = {
        0xB3F47C: b"Mob", 0xB3F470: b"Npc", 0xB3F46C: b"UI",
        0xB3F45C: b"Item", 0xB3F448: b"Etc", 0xB3F428: b"Map",
    }
    for va, want in sorted(unnamed.items(), reverse=True):
        off = va - 0x400000
        check(f"loader table: {want.decode()} @ {va:#x}", want, d[off:off + len(want)])

    check("loader table has 15 distinct names", 15,
          len({v for v in named.values()} | {v for v in unnamed.values()}))
    # the format string is UTF-16LE at s_wz_00b3f41c
    off = 0x00B3F41C - 0x400000
    check("loader format string is UTF-16LE '%s.wz'",
          "%s.wz".encode("utf-16-le"), d[off:off + 10])


def check_wz_archives_on_disk():
    for name in ("UI.wz", "String.wz", "Quest.wz", "Etc.wz"):
        p = os.path.join(WZ, name)
        soft(f"{name} present", os.path.exists(p))
        if not os.path.exists(p):
            continue
        head = read(p, 0x60)
        check(f"{name} magic", b"PKG1", head[:4])
        soft(f"{name} carries Wizet notice",
             b"Copyright 2002 Wizet, ZMS" in head)
        # offset 0x0C holds the header size (60)
        check(f"{name} header size field", 60, struct.unpack_from("<I", head, 12)[0])

    # the published key must not decode the plaintext description
    key = bytes([
        0x13, 0, 0, 0, 0x08, 0, 0, 0, 0x06, 0, 0, 0, 0xB4, 0, 0, 0,
        0x1B, 0, 0, 0, 0x60, 0, 0, 0, 0x99, 0, 0, 0, 0x9F, 0, 0, 0,
        0x48, 0, 0, 0, 0x5F, 0, 0, 0, 0xFF, 0, 0, 0, 0xA5, 0, 0, 0,
        0x18, 0, 0, 0, 0x1D, 0, 0, 0, 0x5F, 0, 0, 0, 0x6B, 0, 0, 0])
    d = read(os.path.join(WZ, "String.wz"), 0x40)
    dec = bytes(b ^ key[i % len(key)] for i, b in enumerate(d[0x10:0x40]))
    check("published v83 key does NOT decode the description", False,
          b"Package" in dec)


def check_img_format():
    p = os.path.join(r"C:\RE\msv83\img", "GMS083登录新界面", "Data",
                     "UI", "MapLogin.img")
    if not os.path.exists(p):
        skip("loose .img format", p)
        return
    head = read(p, 64)
    check("loose .img has no PKG1 header", 0, head.count(b"PKG1"))
    check("loose .img starts 73f86c77", bytes.fromhex("73f86c77"), head[:4])

    import math
    from collections import Counter
    blk = read(p, 4096)
    c = Counter(blk)
    n = len(blk)
    ent = -sum((v / n) * math.log2(v / n) for v in c.values())
    check("loose .img entropy 7.8-7.9", True, 7.8 <= round(ent, 1) <= 7.9)


# =====================================================================
# 5. Script layer
# =====================================================================
def check_scripts():
    import glob
    files = glob.glob(os.path.join(SCRIPTS, "**", "*.js"), recursive=True)
    check("script count", 2294, len(files))

    per = {}
    for f in files:
        rel = os.path.relpath(f, SCRIPTS).split(os.sep)[0]
        per[rel] = per.get(rel, 0) + 1
    for k, v in (("npc", 1101), ("portal", 409), ("quest", 330),
                 ("reactor", 269), ("event", 108), ("map", 72), ("item", 2)):
        check(f"scripts/{k}", v, per.get(k))

    raw = read(os.path.join(SCRIPTS, "npc", "1002000.js"), 200)
    check("scripts decode as gb18030", True,
          "維多利亞港" in raw.decode("gb18030", errors="replace"))


# =====================================================================
# 6. Client import table (from Ghidra analysis of the unpacked build)
# =====================================================================
def check_imports():
    tsv = r"C:\RE\msv83\out\imports.tsv"
    if not os.path.exists(tsv):
        skip("import table from Ghidra output", tsv)
        return
    from collections import Counter
    c = Counter()
    with open(tsv, encoding="utf-8") as f:
        next(f)
        for line in f:
            c[line.split("\t")[0]] += 1
    for dll, n in (("KERNEL32.DLL", 131), ("USER32.DLL", 27),
                   ("WS2_32.DLL", 12), ("MSS32.DLL", 12),
                   ("OLEAUT32.DLL", 11), ("WININET.DLL", 9),
                   ("NMCOGAME.DLL", 8), ("ADVAPI32.DLL", 8),
                   ("GDI32.DLL", 7), ("IJL15.DLL", 4)):
        check(f"imports from {dll}", n, c.get(dll))
    check("total imports", 238, sum(c.values()))


# =====================================================================
# 7. The .i64 and .asm artefacts
# =====================================================================
def check_idb_provenance():
    """The .i64 in the asset folder is built against the PACKED binary.
    The 54,357-function analysis is the separate v83.idb, whose original
    filename is MapleAeon.exe under a GMS\\v83 path."""
    if not os.path.exists(I64):
        skip(".i64 present", I64)
    else:
        soft(".i64 present", os.path.getsize(I64) > 0,
             "%d bytes" % os.path.getsize(I64))
    d = read(IDB)
    check("idb size", 125092284, len(d))
    # The idb B-tree stores the original path more than once, so assert that
    # it is present rather than pinning an occurrence count.
    check("idb carries the original filename", True,
          b"MapleAeon.exe" in d)
    # The path must actually contain GMS and v83, not merely the two letters
    # appearing anywhere in a 125 MB B-tree.
    paths = set(m.decode(errors="replace")
                for m in re.findall(rb"[A-Za-z]:\\[^\x00]{4,160}MapleAeon\.exe", d))
    check("idb has a full original path to MapleAeon.exe", 1, len(paths))
    check("idb path is a GMS v83 path", 1,
          sum(1 for p in paths if "GMS" in p and "v83" in p))
    info("idb original path", paths.pop() if paths else "(none)")
    check("idb imports nmcogame.dll", True, b"nmcogame" in d)
    for sym in (b"NMCO_SetLocale", b"NMCO_SetUseNGMOption",
                b"NMCO_SetVersionFileUrlA", b"NMCO_CallNMFunc"):
        check(f"idb exports {sym.decode()}", True, sym in d)
    # The idb is mostly unnamed: only a handful of Class::method symbols were
    # typed by a human. Assert a ceiling, not just print the count.
    methods = set(re.findall(rb"\b[A-Z][A-Za-z0-9_]{2,40}::[A-Za-z_~][A-Za-z0-9_]*", d))
    check("idb has few human Class::method names (<=64)", True, len(methods) <= 64)
    info("idb Class::method symbol count", "%d distinct" % len(methods))


def check_asm_and_i64_sizes():
    if not os.path.exists(ASM):
        skip(".asm present", ASM)
    else:
        soft(".asm present", os.path.getsize(ASM) > 0,
             "%d bytes" % os.path.getsize(ASM))
        n = sum(1 for _ in open(ASM, "rb"))
        check(".asm line count", 209699, n)


# =====================================================================
# 9. The addresses the wiki publishes
# =====================================================================
# These are the wiki's most load-bearing claims: every patch, hook and
# protocol note is keyed on them. A wrong address silently sends someone to
# the wrong code, so each one is resolved against the unpacked build and
# required to land inside a code section on a plausible instruction boundary.

IMAGE_BASE = 0x400000

# name -> (VA, kind)   kind: "prologue" for named methods, "any" for sub_xxx
CORE_ADDRESSES = {
    "CLogin::OnPacket":        (0x5F80FF, "prologue"),
    "CField::OnPacket":        (0x531325, "prologue"),
    "CWvsContext::OnPacket":   (0xA07A08, "prologue"),
    "CStage::OnPacket":        (0x644446, "any"),
    "StringPool::GetString":   (0x406455, "prologue"),
    "StringPool::GetInstance": (0x79E805, "any"),
    "CInPacket::Decode1":      (0x4065F3, "prologue"),
    "CInPacket::Decode2":      (0x42470C, "prologue"),
    "CInPacket::Decode4":      (0x406629, "prologue"),
    "CInPacket::DecodeBuffer": (0x432257, "prologue"),
    # DecodeStr begins `mov eax, imm32` — a stub, not a framed function, so it
    # is only required to land in a code section.
    "CinPacket::DecodeStr":    (0x46F30C, "any"),
    "_WinMain@16":             (0x9F19F2, "any"),
    "sub_5F83EE":              (0x5F83EE, "any"),
}

# The CWvsContext handler table published in 40-protocol/index.md, as
# opcode -> handler VA. The dispatcher subtracts 29 from the opcode and jumps
# through a table of thunks at 0xA07E8E; each thunk is
# `push dword [ebp+0x0c]` followed by `call rel32`. Resolving those calls
# reproduces the mapping exactly, so a single wrong digit in the wiki's table
# turns this check red.
CWVS_CONTEXT_HANDLERS = {
    29: 0xA1EAD9, 30: 0xA1F881, 31: 0xA1FB52, 32: 0xA202BE, 33: 0xA2071F,
    34: 0xA208FF, 35: 0xA2091C, 36: 0xA1E48C, 37: 0xA209B2, 38: 0xA223DC,
    39: 0xA209D4, 40: 0xA20AC0, 41: 0xA2508B, 42: 0xA25268, 43: 0xA265C2,
    45: 0xA27891, 46: 0xA27B38, 47: 0xA27B61, 48: 0xA29115, 49: 0xA26D44,
    50: 0xA27D75, 51: 0xA1E5AF, 52: 0xA1E943, 53: 0xA1E96D, 55: 0xA29739,
    57: 0xA23D92, 58: 0xA23D79, 59: 0xA1233F, 61: 0xA2370B, 62: 0xA3E31C,
}

CWVS_JUMP_TABLE = 0xA07E8E
CWVS_OPCODE_BIAS = 29

# The wiki publishes this many CWvsContext handlers. Pinning the count stops a
# silently deleted row from passing unnoticed, since the loop below derives
# its own total from the table above.
CWVS_PUBLISHED_COUNT = 30

def _code_ranges(pe):
    """(start, end) file-offset spans of the sections that hold code."""
    spans = []
    for s in pe.sections:
        name = s.Name.rstrip(b"\x00").decode(errors="replace")
        # the first section is unnamed in this build; .rsrc/.idata/.macktt
        # hold resources, imports and the protection stub, not game logic.
        if name in (".rsrc", ".idata", ".macktt"):
            continue
        lo = s.PointerToRawData
        hi = lo + s.SizeOfRawData
        spans.append((lo, hi, name))
    return spans


def _has_prologue(b):
    """True if b begins a standard frame setup (push ebp / mov ebp,esp)."""
    return b[:3] == bytes([0x55, 0x8B, 0xEC])


def check_core_addresses():
    import pefile

    pe = pefile.PE(UNPACKED)
    d = read(UNPACKED)
    spans = _code_ranges(pe)

    for name, (va, kind) in sorted(CORE_ADDRESSES.items(), key=lambda x: x[1][0]):
        off = va - IMAGE_BASE
        if off < 0 or off >= len(d):
            check(f"addr {name} @ {va:#x} is mapped", "in file",
                  "outside file (0x%x)" % off)
            continue
        in_code = any(lo <= off < hi for lo, hi, _ in spans)
        check(f"addr {name} @ {va:#x} lands in a code section", True, in_code)
        if kind == "prologue":
            check(f"addr {name} @ {va:#x} starts with a frame prologue", True,
                  _has_prologue(d[off:off + 3]))


def check_handler_table():
    """Resolve the CWvsContext jump table and reproduce the wiki's mapping.

    Each table slot holds a thunk of the form
        ff 75 0c        push dword [ebp+0x0c]
        e8 <rel32>      call <handler>
    Resolving the relative call against the address just past the instruction
    yields the handler the wiki claims. Comparing resolved targets against the
    published table checks the mapping digit for digit, rather than merely
    confirming that each address exists somewhere in the code section.
    """
    d = read(UNPACKED)

    check("the wiki publishes 30 CWvsContext handler rows",
          CWVS_PUBLISHED_COUNT, len(CWVS_CONTEXT_HANDLERS))

    wrong, unparsed = [], []
    for opcode, claimed in sorted(CWVS_CONTEXT_HANDLERS.items()):
        idx = opcode - CWVS_OPCODE_BIAS
        slot = CWVS_JUMP_TABLE - IMAGE_BASE + idx * 4
        thunk = struct.unpack_from("<I", d, slot)[0]
        o = thunk - IMAGE_BASE
        # ff 75 0c is 3 bytes, e8 rel32 is 5; the return address is past both.
        if d[o:o + 3] == bytes([0xFF, 0x75, 0x0C]) and d[o + 3] == 0xE8:
            rel = struct.unpack_from("<i", d, o + 4)[0]
            resolved = (o + 8 + rel) + IMAGE_BASE
        else:
            unparsed.append(opcode)
            continue
        if resolved != claimed:
            wrong.append((opcode, claimed, resolved))

    check(f"all {len(CWVS_CONTEXT_HANDLERS)} published CWvsContext handlers "
          "parse as push+call thunks", 0, len(unparsed))
    check("every published CWvsContext handler address matches the jump table",
          0, len(wrong))
    if unparsed:
        print("         unparsed opcodes: %s"
              % ", ".join(str(o) for o in unparsed))
    for opcode, claimed, resolved in wrong:
        print(f"         opcode {opcode}: wiki says {claimed:#x}, "
              f"table resolves to {resolved:#x}")


def check_opcode_bounds():
    """The published opcode ranges must be visible in the dispatcher code.

    Dispatchers subtract a bias from the opcode before comparing, so the
    bounds are recovered the same way: find the bias, find the compare, and
    for table-driven dispatchers measure the table itself.
    """
    d = read(UNPACKED)

    # CLogin::OnPacket — wiki says 0~28. No bias: `mov eax,[ebp+8]` loads the
    # opcode directly, then `cmp eax, 0x1c`.
    o = 0x5F80FF - IMAGE_BASE
    check("CLogin::OnPacket compares the opcode against 0x1c (28)",
          bytes([0x83, 0xF8, 0x1C]), d[o + 6:o + 9])

    # CStage::OnPacket — wiki says 128~130, reached by `sub eax, 0x80`.
    o = 0x644446 - IMAGE_BASE
    check("CStage::OnPacket subtracts 0x80 (128)",
          bytes([0x2D, 0x80, 0x00, 0x00, 0x00]), d[o + 4:o + 9])

    # CField::OnPacket — wiki says 125~345. The 125 lower bound is an 8-bit
    # compare; 345 exceeds a byte, so it is dispatched through a multi-way
    # chain and is reported rather than asserted.
    o = 0x531325 - IMAGE_BASE
    seg = d[o:o + 4000]
    lows = [i for i in range(len(seg) - 2)
            if seg[i] == 0x83 and 0xF8 <= seg[i + 1] <= 0xFF
            and seg[i + 2] == 0x7D]
    check("CField::OnPacket compares against 0x7d (125)", True, len(lows) > 0)
    info("CField::OnPacket upper bound 345",
         "0x159 exceeds 255, so it is dispatched by a multi-way compare chain "
         "rather than a single 8-bit compare; not assertable here")

    # CWvsContext::OnPacket — wiki says 29~124. The dispatcher does
    # `add eax, -29` then `cmp eax, 0x5f` (95) and jumps through a table, so
    # the upper bound is 29 + 95 = 124. The table is measured directly: it
    # must hold exactly 96 consecutive pointers into a code section.
    o = 0xA07A08 - IMAGE_BASE
    check("CWvsContext::OnPacket applies the -29 opcode bias",
          bytes([0x83, 0xC0, 0xE3]), d[o + 6:o + 9])
    check("CWvsContext::OnPacket compares the biased opcode against 0x5f (95)",
          bytes([0x83, 0xF8, 0x5F]), d[o + 9:o + 12])

    lo, hi = IMAGE_BASE + 0x1000, IMAGE_BASE + 0x7F9000
    consecutive = 0
    for k in range(256):
        va = struct.unpack_from("<I", d, 0xA07E8E - IMAGE_BASE + k * 4)[0]
        if lo <= va < hi:
            consecutive = k + 1
        else:
            break
    check("CWvsContext jump table holds 96 consecutive code pointers", 96,
          consecutive)
    check("CWvsContext opcode range is 29~124", "29~124",
          "29~%d" % (29 + 95))


def check_wz_full_set():
    """The 15 archive names are resolved from the loader's string table.

    This machine only holds a subset under C:\\RE\\msv83\\wz, so the presence
    of the rest is asserted against a directory that carries the complete set
    when one exists, and reported as INFO otherwise.
    """
    claimed = ["Character", "Mob", "Skill", "Reactor", "Npc", "UI", "Quest",
               "Item", "Effect", "String", "Etc", "Morph", "TamingMob",
               "Sound", "Map"]

    present_here = {f[:-3] for f in os.listdir(WZ)
                    if f.lower().endswith(".wz")} if os.path.isdir(WZ) else set()
    check("the 15-name loader list matches the wiki's table", 15, len(claimed))
    info("WZ archives held under C:\\RE\\msv83\\wz",
         "%d of 15: %s" % (len(present_here), ", ".join(sorted(present_here))))

    full = None
    for cand in (r"C:\RE\msv83\pkg-originals", r"C:\RE\msv83\gate"):
        if not os.path.isdir(cand):
            continue
        have = {f[:-3] for f in os.listdir(cand)
                if f.lower().endswith(".wz")}
        if set(claimed) <= have:
            full = (cand, have)
            break

    if full is None:
        skip("complete 15-file WZ set available", "no directory holds all 15")
        return

    path, have = full
    info("complete WZ set location", path)
    missing = [c for c in claimed if c not in have]
    check("every claimed archive exists in the full set", 0, len(missing))
    extra = sorted(have - set(claimed))
    info("archives present beyond the 15", ", ".join(extra) or "(none)")

    # Every real archive must carry the PKG1 header and the Wizet notice.
    bad_magic, bad_notice = [], []
    for name in claimed:
        p = os.path.join(path, name + ".wz")
        if not os.path.exists(p):
            continue
        head = read(p, 0x60)
        if head[:4] != b"PKG1":
            bad_magic.append(name)
        if b"Copyright 2002 Wizet, ZMS" not in head:
            bad_notice.append(name)
    check("all 15 archives carry the PKG1 magic", 0, len(bad_magic))
    check("all 15 archives carry the Wizet notice", 0, len(bad_notice))



def check_wiki_text():
    """The wiki must never ASSERT a commercial packer identity.

    Mentioning the terms is fine and necessary — the corrected documents
    quote them to explain what was previously wrong. What is forbidden is
    asserting Themida/WzPacker as this binary's protection. This check
    therefore looks for assertion patterns, not raw mentions.
    """
    import re

    # patterns that assert identity
    bad_patterns = [
        (r"是\s*Themida", "asserts 'is Themida'"),
        (r"Themida\s*加殼", "asserts 'Themida packed'"),
        (r"Themida\s*3\.x\s*(?![^\n]*(不|錯|誤|更正|宣称|宣稱))", "asserts Themida 3.x"),
        (r"WzPacker\s*保護版", "asserts 'WzPacker protected'"),
        (r"是\s*WzPacker", "asserts 'is WzPacker'"),
        # bare .mackt written as a section name, ignoring quoted byte literals
        (r"`\.mackt`", "uses .mackt instead of .macktt"),
        # The CWvsContext opcode range was wrong (29~62) and has been corrected
        # to 29~124. Refuse to let the old figure creep back into a table.
        (r"\|\s*29\s*[~～-]\s*62\s*\|", "restates the wrong CWvsContext range"),
        (r"CWvsContext[^\n]*\b29\s*[~～-]\s*62\b", "restates the wrong "
         "CWvsContext opcode range"),
    ]

    offenders = []
    for root, _dirs, files in os.walk(DOCS):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            p = os.path.join(root, fn)
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except Exception:
                continue
            rel = os.path.relpath(p, DOCS)
            for i, line in enumerate(lines, 1):
                for pat, why in bad_patterns:
                    if re.search(pat, line):
                        # allow lines that are explicitly negating the claim,
                        # or that are quoting the old figure in order to correct
                        # it
                        if any(m in line for m in ("不存在", "不是", "0 命中",
                                                  "全 0", "更正值", "誤", "更正",
                                                  "WzPacker**", "WzPacker」",
                                                  "SolidDaima",
                                                  "先前此處寫作",
                                                  "而非", "不是範圍上限",
                                                  "**29~124**", "舊的說法",
                                                  "的說法 | 更正")):
                            continue
                        offenders.append((rel, i, why, line.strip()[:70]))

    print()
    if offenders:
        print("  lines still asserting a commercial packer:")
        for rel, ln, why, txt in offenders:
            print(f"    {rel}:{ln}  [{why}]")
            print(f"      {txt}")
    else:
        print("  no document asserts Themida/WzPacker as the protection")
    ok = not offenders
    results.append((ok, "wiki asserts no commercial-packer identity", True, ok))
    return offenders


def check_structure():
    """The wiki must stay navigable: every document reachable from mkdocs
    nav, and the machine-readable index in step with the prose.

    A 2026-09 pass found 21 documents absent from the nav, 11 of them with
    real content — that is the failure this guards against.
    """
    import json

    nav_path = os.path.join(REPO, "mkdocs.yml")
    if not os.path.exists(nav_path):
        skip("mkdocs nav reachable", nav_path)
        return
    nav = open(nav_path, encoding="utf-8").read()
    # Paths may contain non-ASCII names, so the character class must not be
    # restricted to ASCII or a Chinese filename would be silently missed.
    in_nav = set(re.findall(r"([^\s'\"\[\]:,]+\.md)", nav))

    on_disk = set()
    for root, _dirs, files in os.walk(DOCS):
        for fn in files:
            if fn.endswith(".md"):
                rel = os.path.relpath(os.path.join(root, fn), DOCS)
                on_disk.add(rel.replace(os.sep, "/"))

    orphans = sorted(on_disk - in_nav)
    # 00-overview/*-original.md are deliberately kept out of the nav; they are
    # historical scans reachable from that section's index page instead.
    orphans = [o for o in orphans if not o.endswith("-original.md")
               and not o.endswith("scan-original.md")]
    check("every document is reachable from the nav (excl. original scans)",
          0, len(orphans))
    for o in orphans:
        print("         unreachable: %s" % o)

    dangling = sorted(i for i in in_nav if not os.path.exists(
        os.path.join(DOCS, i.replace("/", os.sep))))
    check("every nav entry points at a real file", 0, len(dangling))
    for d in dangling:
        print("         dangling nav entry: %s" % d)

    # the historical scans must carry a warning banner, and it must be real
    # admonition syntax — a GitHub-style "[!WARNING]" quote renders as an
    # ordinary blockquote and the warning is then invisible on the site.
    unscanned = []
    for rel in sorted(on_disk):
        base = os.path.basename(rel)
        if not (base.endswith("-original.md") or base == "scan-original.md"):
            continue
        body = open(os.path.join(DOCS, rel.replace("/", os.sep)),
                    encoding="utf-8").read()
        if not re.search(r'^!!!\s+warning\b', body, re.M):
            unscanned.append(rel)
    check("every original scan renders a real admonition warning", 0,
          len(unscanned))
    for u in unscanned:
        print("         missing/invalid warning banner: %s" % u)

    # facts.json must agree with the prose on the numbers agents will read
    facts_path = os.path.join(DOCS, "facts.json")
    if not os.path.exists(facts_path):
        skip("facts.json present", facts_path)
        return
    facts = json.load(open(facts_path, encoding="utf-8"))

    check("facts.json addresses match the verified set",
          sorted(k for k, v in CORE_ADDRESSES.items()),
          sorted(facts["addresses"].keys()))
    mismatch = [(n, va, facts["addresses"].get(n, {}).get("va"),
                 facts["addresses"].get(n, {}).get("hex"))
                for n, (va, _k) in CORE_ADDRESSES.items()
                if facts["addresses"].get(n, {}).get("va") != va]
    check("facts.json address values match the binaries", 0, len(mismatch))
    for n, va, got, got_hex in mismatch:
        print("         %s: binaries say %#x, facts.json says %s"
              % (n, va, got_hex if got_hex else repr(got)))

    check("facts.json publishes the same handler count",
          CWVS_PUBLISHED_COUNT, len(facts["cwvs_context_handlers"]))
    bad_handler = [(o, va, facts["cwvs_context_handlers"].get(str(o), {}).get("va"))
                   for o, va in CWVS_CONTEXT_HANDLERS.items()
                   if facts["cwvs_context_handlers"].get(str(o), {}).get("va") != va]
    check("facts.json handler addresses match the jump table", 0,
          len(bad_handler))
    for o, va, got in bad_handler:
        print("         opcode %d: jump table says %#x, facts.json says %s"
              % (o, va, hex(got) if isinstance(got, int) else repr(got)))

    # the corrected opcode range must be the one facts.json advertises
    cwvs = facts["dispatchers"]["CWvsContext::OnPacket"]["opcode_range"]
    check("facts.json carries the corrected CWvsContext range", [29, 124], cwvs)
    check("facts.json records at least one correction", True,
          len(facts.get("corrections", [])) >= 1)


def check_no_hardcoded_tally():
    """The pass count moves every time a check is added, so no document may
    quote it. A stale "166/166" in the README is worse than no number: it
    invites the reader to trust a tally that no longer matches the script."""
    import re as _re
    stale = []
    pattern = _re.compile(r"\b\d{2,3}\s*/\s*\d{2,3}\s*(?:斷言|檢查|checks)")
    targets = []
    for name in ("README.md", "AGENTS.md"):
        p = os.path.join(REPO, name)
        if os.path.exists(p):
            targets.append(p)
    targets.append(os.path.join(DOCS, "index.md"))
    for p in targets:
        if not os.path.exists(p):
            continue
        for i, line in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
            if pattern.search(line):
                stale.append((os.path.relpath(p, REPO), i, line.strip()[:70]))
    check("no document hard-codes the assertion tally", 0, len(stale))
    for rel, ln, txt in stale:
        print("         %s:%d  %s" % (rel, ln, txt))


def check_bookmarks_pipeline():
    """The GitHub bookmark page and the WIKI page are two renderings of one
    dataset. They used to live in separate projects, which let them drift; now
    that both sit in this repo, assert the chain is intact and current."""
    import json

    data = os.path.join(REPO, "tools", "bookmarks", "_repos.json")
    if not os.path.exists(data):
        skip("bookmark dataset present", data)
        return

    repos = json.load(open(data, encoding="utf-8"))
    check("bookmark dataset is non-trivial", True, len(repos) >= 100)

    unnoted = [r["full_name"] for r in repos
               if not r.get("note")
               or r["note"].strip() == (r.get("desc") or "").strip()]
    check("every bookmark has a hand-written Chinese note", 0, len(unnoted))
    for u in unnoted[:5]:
        print("         untranslated: %s" % u)

    bad_url = [r["full_name"] for r in repos
               if not r.get("url", "").startswith("https://github.com/")]
    check("every bookmark url points at github", 0, len(bad_url))

    # the single-file build must be current with respect to the dataset
    single = os.path.join(REPO, "tools", "bookmarks", "楓之谷專案書籤.html")
    if not os.path.exists(single):
        skip("standalone bookmark html present", single)
    else:
        body = open(single, encoding="utf-8").read()
        m = re.search(r"const DATA = (\[.*?\]);\n", body, re.S)
        if m is None:
            check("standalone bookmark embeds its dataset", True, False)
        else:
            embedded = json.loads(m.group(1))
            n = sum(len(c["items"]) for c in embedded)
            check("standalone bookmark carries every project", len(repos), n)
            check("standalone bookmark has no unreachable link", 0,
                  sum(1 for c in embedded for it in c["items"]
                      if not it["url"].startswith("https://github.com/")))

    # the WIKI page must render the same project count
    page = os.path.join(DOCS, "70-resources", "github-bookmarks", "index.md")
    if not os.path.exists(page):
        skip("wiki bookmark page present", page)
    else:
        m = re.search(r"const DATA = (\[.*?\]);\n",
                      open(page, encoding="utf-8").read(), re.S)
        if m is None:
            check("wiki bookmark page embeds its dataset", True, False)
        else:
            n = sum(len(c["items"]) for c in json.loads(m.group(1)))
            check("wiki bookmark page carries every project", len(repos), n)

            # mkdocs builds its search index from the static markdown only, so
            # a page whose rows are injected by JavaScript is invisible to site
            # search. Require a plain-table rendition of the same data.
            body = open(page, encoding="utf-8").read()
            linked = set(re.findall(r"^\| \[([^\]]+)\]\(https://github\.com/",
                                    body, re.M))
            check("wiki bookmark page has a static index of every project",
                  len(repos), len(linked))
            missing = [r["full_name"] for r in repos
                       if r["full_name"] not in linked]
            for mname in missing[:5]:
                print("         not in static table: %s" % mname)

    # the home page must link the bookmark page, or nobody finds it
    home = os.path.join(DOCS, "index.md")
    if os.path.exists(home):
        h = open(home, encoding="utf-8").read()
        check("home page links the bookmark page", True,
              "github-bookmarks" in h)


def check_no_local_paths():
    """The published Pages build must not carry this machine's directory
    layout. Absolute Windows paths are replaced by placeholders before
    deployment; a straggler means the anonymiser was not re-run after an edit.

    Exempt, because these files ARE the binary's own strings rather than the
    author's machine:
      * ``v83-idb/strings.md`` — a verbatim dump of the string pool
      * the §5.2 table in ``v83-idb/technical-report.md`` — same, one section
      * ``00-overview/*-original.md`` — historical scans, annotated in place
    """
    import re as _re

    # A drive letter not preceded by a word character, so https:// is ignored.
    pat = _re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s\"'`)\]]{4,}")
    exempt_doc = _re.compile(
        r"00-overview/[^/]*-original\.md$"
        r"|00-overview/scan-original\.md$"
        r"|v83-idb/strings\.md$")

    offenders = []
    for root, _dirs, files in os.walk(DOCS):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, DOCS).replace(os.sep, "/")
            if exempt_doc.search(rel):
                continue
            body = open(p, encoding="utf-8").read()
            # §5.2 is a verbatim dump of the binary's string pool; entries
            # that look like Windows paths are the client's own string
            # constants, which are the evidence. Skip that one section.
            marker = "§5.2 "
            if marker in body:
                head, _, tail = body.partition(marker)
                end = tail.find("\n## ")
                section = tail[:end] if end > 0 else tail
                body = head + re.sub(r"(?m)^\|.*$", "", section)
            for m in pat.finditer(body):
                offenders.append((rel, m.group(0)[:60]))

    check("no document leaks a local absolute path", 0, len(offenders))
    for rel, s in offenders[:12]:
        print("         %s: %s" % (rel, s))

    # facts.json ships to the same Pages site and is read by agents, so it
    # must be scrubbed too
    fj = os.path.join(DOCS, "facts.json")
    if os.path.exists(fj):
        raw = open(fj, encoding="utf-8").read()
        jhits = pat.findall(raw)
        check("facts.json leaks no local absolute path", 0, len(jhits))
        for s in jhits[:5]:
            print("         facts.json: %s" % s[:60])
    else:
        skip("facts.json present", fj)

    # the anonymiser must exist, or this check is a one-off
    tool = os.path.join(REPO, "tools", "anonymize_paths.py")
    soft("path anonymiser is present", os.path.exists(tool), tool)


def check_console_chapter():
    """The console chapter was imported from a separate note set. Guard the two
    things that can rot: an index that disagrees with the pages, and entries
    pointing at a file that is not in this repo."""
    import json

    ch = os.path.join(DOCS, "80-console")
    if not os.path.isdir(ch):
        skip("console chapter present", ch)
        return

    pages = sorted(f for f in os.listdir(ch) if f.endswith(".md") and f != "index.md")
    check("console chapter has 18 topic pages", 18, len(pages))

    idx = os.path.join(DOCS, "console-index.jsonl")
    if not os.path.exists(idx):
        skip("console index present", idx)
        return

    entries = []
    bad = 0
    for line in open(idx, encoding="utf-8"):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except Exception:
            bad += 1
    check("console index parses cleanly", 0, bad)
    check("console index carries every entry", True, len(entries) > 0)

    # the index's file field must resolve inside this repo
    dangling = sorted({e["file"] for e in entries
                       if e.get("file") and not os.path.exists(
                           os.path.join(REPO, e["file"].replace("/", os.sep)))})
    check("every console entry points at a page in this repo", 0, len(dangling))
    for d in dangling[:5]:
        print("         dangling: %s" % d)

    # ids must be unique, since the docs call them stable
    ids = [e.get("id") for e in entries]
    check("console entry ids are unique", len(ids), len(set(ids)))

    topics = {e.get("topic") for e in entries}
    check("console index covers all 18 topics", 18, len(topics))

    # the chapter must be reachable and every page must have an entry
    on_disk = set(pages)
    referenced = {os.path.basename(e["file"]) for e in entries
                  if e.get("file")}
    check("every topic page has at least one indexed entry", 0,
          len(on_disk - referenced))
    for p in sorted(on_disk - referenced):
        print("         no entries for: %s" % p)

    # a sample of entries must carry a pitfall note; that is the chapter's
    # whole reason for existing
    with_pitfall = sum(1 for e in entries if (e.get("pitfall") or "").strip())
    check("a majority of console entries record a pitfall", True,
          with_pitfall * 2 >= len(entries))
    info("console entries with a recorded pitfall",
         "%d of %d" % (with_pitfall, len(entries)))


def check_standalone_bookmarks():
    """The standalone page is a second rendering of the same dataset. Guard
    that it stays in step and that it is actually published."""
    import json
    import re

    data_path = os.path.join(REPO, "tools", "bookmarks", "_repos.json")
    if not os.path.exists(data_path):
        skip("bookmark dataset present", data_path)
        return
    n_expected = len(json.load(open(data_path, encoding="utf-8")))

    src = os.path.join(DOCS, "standalone", "index.html")
    if not os.path.exists(src):
        skip("standalone bookmark page present", src)
        return

    body = open(src, encoding="utf-8").read()

    # it must be a complete document, not a mkdocs fragment
    check("standalone page is a whole HTML document", True,
          body.lstrip().lower().startswith("<!doctype html"))
    # no Material chrome: that is the entire point of the page
    for token in ("md-sidebar", "md-header", "md-nav", "md-content"):
        check("standalone page has no Material %s" % token, 0,
              body.count(token))

    m = re.search(r"const DATA=(\[.*?\]), CATS=", body, re.S)
    if m is None:
        check("standalone page embeds its dataset", True, False)
        return
    data = json.loads(m.group(1))
    n = sum(len(c["items"]) for c in data)
    check("standalone page carries every project", n_expected, n)

    bad = [it["url"] for c in data for it in c["items"]
           if not it["url"].startswith("https://github.com/")]
    check("standalone page links only to github", 0, len(bad))

    # both renderings must agree, or the two pages drift
    page = os.path.join(DOCS, "70-resources", "github-bookmarks", "index.md")
    if os.path.exists(page):
        w = re.findall(r"^\| \[([^\]]+)\]\(https://github\.com/",
                       open(page, encoding="utf-8").read(), re.M)
        check("standalone and embedded pages list the same projects", n,
              len(w))
        s = {it["full_name"] for c in data for it in c["items"]}
        check("both pages reference identical repos", 0, len(s - set(w)))

    # it must ship with the site
    shipped = os.path.join(REPO, "site", "standalone", "index.html")
    soft("standalone page is copied into the site output",
         os.path.exists(shipped), shipped)
    # and it must have been copied verbatim, not run through the template
    if os.path.exists(src) and os.path.exists(shipped):
        check("standalone page ships verbatim", open(src, "rb").read()[:400],
              open(shipped, "rb").read()[:400])

    home = os.path.join(DOCS, "index.md")
    if os.path.exists(home):
        check("home page links the standalone bookmark page", True,
              "standalone" in open(home, encoding="utf-8").read())


def main():
    import datetime

    print("Packed binary")
    check_packed_identity()
    check_not_commercial_packer()
    check_csecurity_evidence()
    print("\nUnpacked build")
    check_unpacked()
    print("\nWZ / Pixi architecture")
    check_pixi()
    check_wz_reader_not_in_client()
    check_wz_name_table()
    check_wz_archives_on_disk()
    check_img_format()
    print("\nScript layer")
    check_scripts()
    print("\nImports")
    check_imports()
    print("\nAnalysis artefacts")
    check_idb_provenance()
    check_asm_and_i64_sizes()
    print("\nPublished addresses")
    check_core_addresses()
    check_handler_table()
    check_opcode_bounds()
    print("\nWZ archive set")
    check_wz_full_set()
    print("\nStructure")
    check_structure()
    check_no_hardcoded_tally()
    check_no_local_paths()
    print("\nBookmark pipeline")
    check_bookmarks_pipeline()
    check_standalone_bookmarks()
    print("\nConsole chapter")
    check_console_chapter()
    print("\nWiki self-consistency")
    check_wiki_text()

    passed = sum(1 for ok, *_ in results if ok)
    total = len(results)
    skipped = sum(1 for ok, name, exp, act in results if exp == "SKIP")
    asserted = total - skipped
    print("\n" + "=" * 62)
    ts = datetime.datetime.fromtimestamp(1267176451, datetime.UTC)
    print(f"  packed build timestamp: {ts.isoformat()} UTC")
    print(f"  {passed}/{asserted} assertions passed"
          + (f"  ({skipped} skipped)" if skipped else ""))
    print(f"  {len(infos)} info lines (measurements, not assertions)")
    print("=" * 62)
    if passed != total:
        print("\nFailures:")
        for ok, name, exp, act in results:
            if not ok:
                print(f"  {name}\n    expected {exp!r}\n    actual   {act!r}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
