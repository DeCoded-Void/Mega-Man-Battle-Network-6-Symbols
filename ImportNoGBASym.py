# -*- coding: utf-8 -*-
# Rename existing functions/symbols from a no$gba .sym without creating new functions.
# Prefers renaming an existing PRIMARY symbol at the address and creates a label if nothing exists.
#@author de.coded
#@category Import
#@menupath Tools.Rename Functions from .sym 

import re
from ghidra.program.model.symbol import SourceType

# ---- USER TOGGLES ----
CREATE_LABEL_IF_MISSING = True    # If no function/symbol exists at address, create a label
REPORT_ONLY = False               # Dry-run to log actions only

def parse_line(line):
    m = re.match(r'^([0-9A-Fa-f]{8})\s+(\S+)', line.strip())
    if not m:
        return None
    addr_str, name = m.group(1).upper(), m.group(2)
    if name.startswith('.'):
        return ('directive', addr_str, name)
    return ('symbol', addr_str, name)

def even_hex(addr_hex):
    v = int(addr_hex, 16) & ~1
    return "%08X" % v

def main():
    symfile = askFile("Select .sym file", "Open")
    if symfile is None:
        print("No file selected.")
        return

    lines = open(symfile.absolutePath, 'r').read().splitlines()

    renamed_fn = 0
    renamed_sym = 0
    labeled = 0
    skipped = 0
    collisions = 0

    symtab = currentProgram.getSymbolTable()
    listing = currentProgram.getListing()

    for line in lines:
        parsed = parse_line(line)
        if not parsed:
            continue
        kind, addr_hex, new_name = parsed
        if kind != 'symbol':
            continue

        entry_hex = even_hex(addr_hex)
        addr = toAddr(entry_hex)
        if addr is None:
            skipped += 1
            print("[skip] bad address %s %s" % (entry_hex, new_name))
            continue

        # 1) If a function exists at/containing the address, rename the FUNCTION
        f = getFunctionAt(addr)
        if f is None:
            f = getFunctionContaining(addr)
        if f is not None:
            try:
                old = f.getName()
                if old != new_name:
                    if REPORT_ONLY:
                        print("[would rename-func] %s -> %s at %s" % (old, new_name, entry_hex))
                    else:
                        f.setName(new_name, SourceType.IMPORTED)
                        print("[renamed-func] %s -> %s at %s" % (old, new_name, entry_hex))
                    renamed_fn += 1
                continue
            except Exception as e:
                print("[func rename failed] %s at %s (%s)" % (new_name, entry_hex, str(e)))
                collisions += 1

        # 2) Try to rename existing primary symbol at address
        primary = symtab.getPrimarySymbol(addr)
        if primary is not None:
            try:
                old = primary.getName()
                if old != new_name:
                    if REPORT_ONLY:
                        print("[would rename-sym] %s -> %s at %s" % (old, new_name, entry_hex))
                    else:
                        primary.setName(new_name, SourceType.IMPORTED)
                        print("[renamed-sym] %s -> %s at %s" % (old, new_name, entry_hex))
                    renamed_sym += 1
                continue
            except Exception as e:
                print("[sym rename failed] %s at %s (%s)" % (new_name, entry_hex, str(e)))
                collisions += 1

        # 3) Try non-primary symbols at the same address
        syms = symtab.getSymbols(addr)
        did_one = False
        for s in syms:
            try:
                if s.getName() == new_name:
                    did_one = True
                    break
                if REPORT_ONLY:
                    print("[would rename-sym*] %s -> %s at %s" % (s.getName(), new_name, entry_hex))
                else:
                    s.setName(new_name, SourceType.IMPORTED)
                    print("[renamed-sym*] %s -> %s at %s" % (s.getName(), new_name, entry_hex))
                renamed_sym += 1
                did_one = True
                break
            except Exception:
                pass
        if did_one:
            continue

        # 4) If nothing exists at the address, create a PRIMARY label
        if CREATE_LABEL_IF_MISSING:
            try:
                if REPORT_ONLY:
                    print("[would label] %s at %s" % (new_name, entry_hex))
                else:
                    createLabel(addr, new_name, True, SourceType.IMPORTED)
                    print("[labeled] %s at %s" % (new_name, entry_hex))
                labeled += 1
                continue
            except Exception as e:
                print("[label failed] %s at %s (%s)" % (new_name, entry_hex, str(e)))
                skipped += 1
                continue

        skipped += 1
        print("[skip] nothing to rename at %s for %s" % (entry_hex, new_name))

    print("Done: renamed_fn=%d, renamed_sym=%d, labeled=%d, collisions=%d, skipped=%d" %
          (renamed_fn, renamed_sym, labeled, collisions, skipped))

if __name__ == "__main__":
    main()
