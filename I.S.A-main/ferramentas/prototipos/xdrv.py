"""Driver externo: injeta teclado/mouse via XTEST no Xvfb e tira capturas do X (import)."""
import time, subprocess, os
from Xlib import X, XK, display
from Xlib.ext import xtest
os.environ.setdefault("DISPLAY", ":99")
D = display.Display(os.environ["DISPLAY"])
EVID = os.environ.get("EVID", "/home/claude/evid")
def kc(nome): return D.keysym_to_keycode(XK.string_to_keysym(nome))
def down(nome): xtest.fake_input(D, X.KeyPress, kc(nome)); D.sync()
def up(nome): xtest.fake_input(D, X.KeyRelease, kc(nome)); D.sync()
def tap(nome, hold=0.08): down(nome); time.sleep(hold); up(nome); time.sleep(0.05)
def hold(nome, seg): down(nome); time.sleep(seg); up(nome)
def typ(txt):
    for ch in txt: tap(ch)
def click(x, y):
    xtest.fake_input(D, X.MotionNotify, x=x, y=y); D.sync(); time.sleep(0.15)
    xtest.fake_input(D, X.ButtonPress, 1); D.sync(); time.sleep(0.08)
    xtest.fake_input(D, X.ButtonRelease, 1); D.sync(); time.sleep(0.1)
def move(x, y): xtest.fake_input(D, X.MotionNotify, x=x, y=y); D.sync()
def shot(nome):
    p = os.path.join(EVID, nome + ".png")
    subprocess.run(["import", "-window", "root", "-crop", "800x600+0+0", p], check=True)
    return p

def janela():
    r = D.screen().root
    for w in r.query_tree().children:
        if w.get_attributes().map_state == 2:
            g = w.get_geometry(); return g.x, g.y, g.width, g.height
def shot(nome):
    x, y, w, h = janela()
    p = os.path.join(EVID, nome + ".png")
    subprocess.run(["import", "-window", "root", "-crop", f"{w}x{h}+{x}+{y}", "+repage", p], check=True)
    return p
def clickw(x, y):
    """clique em coordenadas da janela do jogo"""
    jx, jy, _, _ = janela(); click(jx + x, jy + y)
