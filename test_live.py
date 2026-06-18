"""Dev harness: launch with kitten adopted and a mouse arriving in ~5 s."""
import time

import vcat

vcat.set_dpi_aware()
state = vcat.load_state()
state["kitten"] = True
app = vcat.VCat(state)
app.next_mouse = time.monotonic() + 5
app.mainloop()
