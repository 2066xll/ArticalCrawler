# Fix Chapter Count Logic Bug

## Problem Analysis

The issue is a mismatch between the chapter count conversion in `app.py` and the updated logic in the crawler script:

1. **User Input**: When user enters 3 chapters in the UI
2. **app.py Conversion**: Currently converts to `-n 2` (because `adjusted_next_chapters = next_chapters - 1`)
3. **Crawler Logic**: Now treats `-n` as total chapters (not "next chapters after current")
4. **Result**: Crawler fetches 2 chapters instead of 3, causing user frustration

## Root Cause

We changed the crawler's `main()` function to treat `-n` as total chapters:

```python
chapters_to_fetch = args.next_chapters if args.next_chapters > 0 else 1
```

But we forgot to update the conversion in `app.py`, which was compensating for the old logic:

```python
crawler_next_chapters = next_chapters - 1 if next_chapters > 0 else 0
```

## Fix

Remove the conversion in `app.py` and directly pass the user's chapter count as the `-n` parameter:

1. **Modify** **`app.py`**: Remove the `crawler_next_chapters` calculation
2. **Direct Parameter Passing**: Use `next_chapters` directly in the command
3. **Consistent Logic**: Ensure user input matches crawler expectation

## Expected Result

* User enters 3 chapters → `app.py` passes `-n 3` → crawler fetches 3 chapters

* User enters 1 chapter → `app.py` passes `-n 1` → crawler fetches 1 chapter

* All cases match user expectations

## Testing

1. Test with user input 3 → verify 3 chapters generated
2. Test with user input 1 → verify 1 chapter generated
3. Test with user input 0 → verify at least 1 chapter generated

## File Changes

* `app.py`: Remove chapter count conversion, direct parameter passing

