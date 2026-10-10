from .common import UVLocation

class Atlas:
    def __init__(self, width: int, height: int, occupation: str, padding: int=0) -> None:
        self.occupation = occupation
        self.width = width
        self.height = height
        self.padding = padding
        self.tex_id = -1

        initial = UVLocation(0, 0, width, height)
        self.free_rects: dict[tuple[int, int, int, int], UVLocation] = {(initial.x, initial.y, initial.w, initial.h): initial}
        self.used_rects: dict[tuple[int, int, int, int], UVLocation] = {}

    def insert(self, w: int, h: int) -> UVLocation | None:
        w += self.padding
        h += self.padding

        best = None
        best_score = float("inf")

        for r in self.free_rects.values():
            if w <= r.w and h <= r.h:
                leftover_h = abs(r.h - h)
                leftover_w = abs(r.w - w)
                short_side = min(leftover_h, leftover_w)

                if short_side < best_score:
                    best = UVLocation(r.x, r.y, w, h)
                    best_score = short_side

        if best is None:
            return None

        self._place(best)
        return UVLocation(best.x, best.y, w - self.padding, h - self.padding)

    def _place(self, rect: UVLocation):
        new_free: list[UVLocation] = []

        for free in self.free_rects.values():
            if not self._intersect(rect, free):
                new_free.append(free)
                continue

            if rect.x > free.x:
                new_free.append(UVLocation(free.x, free.y, rect.x - free.x, free.h))

            if rect.x + rect.w < free.x + free.w:
                new_free.append(UVLocation(
                    rect.x + rect.w,
                    free.y,
                    (free.x + free.w) - (rect.x + rect.w),
                    free.h
                ))

            if rect.y > free.y:
                new_free.append(UVLocation(free.x, free.y, free.w, rect.y - free.y))

            if rect.y + rect.h < free.y + free.h:
                new_free.append(UVLocation(
                    free.x,
                    rect.y + rect.h,
                    free.w,
                    (free.y + free.h) - (rect.y + rect.h)
                ))

        pruned = self._prune(new_free)
        self.free_rects = {
            (r.x, r.y, r.w, r.h): r for r in pruned
        }
        self.used_rects[(rect.x, rect.y, rect.w, rect.h)] = rect

    def _intersect(self, a: UVLocation, b: UVLocation):
        return not (
            a.x >= b.x + b.w or
            a.x + a.w <= b.x or
            a.y >= b.y + b.h or
            a.y + a.h <= b.y
        )

    def _contains(self, a: UVLocation, b: UVLocation):
        return (
            a.x <= b.x and
            a.y <= b.y and
            a.x + a.w >= b.x + b.w and
            a.y + a.h >= b.y + b.h
        )

    def _prune(self, rects: list[UVLocation]):
        pruned: list[UVLocation] = []
        for i, r in enumerate(rects):
            contained = False
            for j, other in enumerate(rects):
                if i != j and self._contains(other, r):
                    contained = True
                    break
            if not contained:
                pruned.append(r)
        return pruned
    
    def remove(self, rect: "UVLocation") -> bool:
        key = (rect.x, rect.y, rect.w, rect.h)

        if key not in self.used_rects:
            return False

        del self.used_rects[key]

        self.free_rects[key] = UVLocation(rect.x, rect.y, rect.w, rect.h)

        self._merge_free_rects()

        return True

    def _merge_free_rects(self) -> None:
        merged = True
        
        while merged:
            merged = False
            rects = list(self.free_rects.values())

            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    a = rects[i]
                    b = rects[j]

                    merged_rect = self._try_merge(a, b)
                    if merged_rect:
                        del self.free_rects[(a.x, a.y, a.w, a.h)]
                        del self.free_rects[(b.x, b.y, b.w, b.h)]

                        self.free_rects[
                            (merged_rect.x, merged_rect.y, merged_rect.w, merged_rect.h)
                        ] = merged_rect

                        merged = True
                        break
                if merged:
                    break

        pruned = self._prune(list(self.free_rects.values()))
        self.free_rects = {
            (r.x, r.y, r.w, r.h): r for r in pruned
        }

    def _try_merge(self, a: "UVLocation", b: "UVLocation") -> UVLocation | None:
        if a.y == b.y and a.h == b.h:
            if a.x + a.w == b.x:
                return UVLocation(a.x, a.y, a.w + b.w, a.h)
            if b.x + b.w == a.x:
                return UVLocation(b.x, b.y, a.w + b.w, a.h)

        if a.x == b.x and a.w == b.w:
            if a.y + a.h == b.y:
                return UVLocation(a.x, a.y, a.w, a.h + b.h)
            if b.y + b.h == a.y:
                return UVLocation(b.x, b.y, a.w, a.h + b.h)

        return None
