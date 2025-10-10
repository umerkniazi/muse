import curses
import difflib
import hashlib

def key_match(key, options, buffer=None):
    for opt in options:
        if isinstance(opt, int) and key == opt:
            return True
        if isinstance(opt, str):
            if opt.startswith("KEY_"):
                if hasattr(curses, opt) and key == getattr(curses, opt):
                    return True
            elif len(opt) == 1 and key == ord(opt):
                return True
            elif buffer is not None and buffer == opt:
                return True
    return False

def search(query, names):
    if not query.strip():
        return list(range(len(names)))
    query_lower = query.lower()
    exact_matches = []
    starts_with_matches = []
    word_matches = []
    fuzzy_matches = []
    substring_matches = []
    for i, name in enumerate(names):
        name_lower = name.lower()
        if name_lower == query_lower:
            exact_matches.append(i)
        elif name_lower.startswith(query_lower):
            starts_with_matches.append(i)
        elif any(word.startswith(query_lower) for word in name_lower.split()):
            word_matches.append(i)
        elif query_lower in name_lower:
            substring_matches.append(i)
    fuzzy_candidates = [i for i in range(len(names)) if i not in exact_matches + starts_with_matches + word_matches + substring_matches]
    if fuzzy_candidates:
        fuzzy_names = [names[i] for i in fuzzy_candidates]
        fuzzy_indices = [i for i, name in zip(fuzzy_candidates, fuzzy_names) if name]
        fuzzy_matches_raw = difflib.get_close_matches(query, fuzzy_names, n=len(fuzzy_names), cutoff=0.5)
        fuzzy_matches = [i for i, name in zip(fuzzy_candidates, fuzzy_names) if name in fuzzy_matches_raw]
    all_matches = exact_matches + starts_with_matches + word_matches + substring_matches + fuzzy_matches
    return all_matches

def get_folder_hash(path):
    return hashlib.md5(path.encode("utf-8")).hexdigest()