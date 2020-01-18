#!/usr/bin/env python3
# Author: Armit
# Create time: 2019/09/27 
# Update time: 2020/01/18

import sys, os
from os import path
import logging
import re
import gzip
import pickle
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from tkinter import filedialog
from tkinter import colorchooser

__version__ = '0.1'

TYPEFACE_DEFAULT = {
  'font': 'scroll',     # { sculpture, scroll, handwriting }
  'size': 10,           # 5 ~ 15
  'clarity': 0,         # -5 ~ 5 (bold)
  'italic': False,      # 15° inclination
  'color': None,        # as a mask
  'char_spacing': 0,    # -5 ~ 5
  'line_spacing': 0,    # -5 ~ 5
  'hw_ratio': 1.0,      # 0.5 ~ 1.5
}

BASE_PATH = path.dirname(path.abspath(__file__))
FONTSET_PATH = path.join(BASE_PATH, 'fonts')
OUT_PATH = path.join(BASE_PATH, 'out')
ZIPMOD = gzip
WINDOW_SIZE = (800, 600)  # (1024, 768)
EDITOR_LINES = 8          # 12
EDITOR_FONT = ('Times New Roman', 14)
LABEL_PADX = 4
COMBOBOX_WIDTH = 12
COLORSEL_WIDTH = 8
SPINBOX_WIDTH = 4

os.makedirs(FONTSET_PATH, exist_ok=True)
os.makedirs(OUT_PATH, exist_ok=True)

# Mapping latinization to semi-syllable tokens
def tokenize(self, latinization) -> [[str]]:
  ret = [ ]
  for line in latinization.split('\n'):
    ret += line.split(' ')
  return ret

class FontLibrary:

  FONTS = { }     # { 'name': { char: Image } }

  @classmethod
  def get(cls, name) -> { str: Image.Image }:
    if name not in cls.FONTS:
      fn_pkl = path.join(FONTSET_PATH, name + '.pkl')
      if path.exists(fn_pkl):
          with ZIPMOD.open(fn_pkl, 'rb') as fp:
            cls.FONTS[name] = pickle.load(fp)
          logging.info('[%s] loading cached font %r' % (cls.__name__, name))
      else:
        logging.info('[%s] building cache for font %r' % (cls.__name__, name))
        fontset = { }
        dp = path.join(FONTSET_PATH, name)
        for fn in os.listdir(dp):
          char_name = path.splitext(fn)[0]
          fontset[char_name] = Image.open(path.join(dp, fn)).convert('L')
        cls.FONTS[name] = fontset

        with ZIPMOD.open(fn_pkl, 'wb+') as fp:
          pickle.dump(fontset, fp, protocol=4)
    return cls.FONTS.get(name)

class Typesetter:

  class Token:

    def __init__(self, body=None, nota_upper=None, nota_lower=None):
      self.body = body              # Image
      self.nota_upper = nota_upper  # Image
      self.nota_lower = nota_lower  # Image

    def width(self):
      return 0

    def height(self):
      return 0

  class Line:

    def __init__(self, token_margin=0):
      self.chars = [ ]
      self.token_margin = token_margin

    def __setitem__(self, idx, val):
      self.chars[idx] = val

    def __getitem__(self, idx):
      return self.chars[idx]
    
    def __iadd__(self, char):
      self.chars.append(char)

    def width(self):
      return 0

    def height(self):
      return 0

  class Text:

    def __init__(self, line_margin=0):
      self.lines = [ ]
      self.line_margin = line_margin
    
    def __setitem__(self, idx, val):
      self.lines[idx] = val
    
    def __getitem__(self, idx):
      return self.lines[idx]

    def __iadd__(self, line):
      self.lines.append(line)
    
    def width(self):
      return 0

    def height(self):
      return 0
  
  def print(self, text, **configs):
    # prepare fontset library
    fs = FontLibrary.get(configs.get('font', TYPEFACE_DEFAULT['font']))

    # typeset/format: process 'char/line spacing'
    tx = self.Text(margin=configs.get('line_spacing', TYPEFACE_DEFAULT['line_spacing']))
    for line in tokenize(text):
      ln = self.Line(margin=configs.get('char_spacing', TYPEFACE_DEFAULT['char_spacing']))
      for tok in line:
        # TODO: tok -> (body, nota_upper, note_lower)
        body = fs.get(tok)
        nota_upper, note_lower = None, None
        ln += self.Token(body, nota_upper, note_lower)
      tx += ln

    # print frame to image
    canvas = Image.new('L', (tx.width(), tx.height()))
    for let in let_imgs:
      box = (w, 0)
      out.paste(let, box)
      w += let.width
    
    # image after effect tranformations: process 'size/clarity/italic/color/hw_ratio'
    size = configs.get('size', TYPEFACE_DEFAULT['size'])
    clarity = configs.get('clarity', TYPEFACE_DEFAULT['clarity'])
    italic = configs.get('italic', TYPEFACE_DEFAULT['italic'])
    color = configs.get('color', TYPEFACE_DEFAULT['color'])
    hw_ratio = configs.get('hw_ratio', TYPEFACE_DEFAULT['hw_ratio'])
    
    return canvas

class App:

  def __init__(self):
    self.typesetter = Typesetter()

    logging.debug('[%s] init' % self.__class__.__name__)
    self.setup_gui()
    logging.debug('[%s] ready' % self.__class__.__name__)
    try: tk.mainloop()
    except KeyboardInterrupt: pass
    logging.debug('[%s] bye' % self.__class__.__name__)
  
  def setup_gui(self):
    # root window
    wnd = tk.Tk()
    wnd.title('Ion Writer (Ver %s)' % __version__)
    (wndw, wndh), scrw, scrh = WINDOW_SIZE, wnd.winfo_screenwidth(), wnd.winfo_screenheight()
    wnd.geometry('%dx%d+%d+%d' % (wndw, wndh, (scrw - wndw) // 2, (scrh - wndh) // 4))
    wnd.resizable(False, False)
    self.wnd = wnd

    # menu
    menu = tk.Menu(wnd, tearoff=False)
    menu.add_command(label="Refresh", command=lambda: self.view())
    menu.add_separator()
    menu.add_command(label="Save", command=lambda: self.save('default'))
    menu.add_command(label="Save As..", command=lambda: self.save('select'))
    # wnd.config(menu=menu)
    self.menu = menu

    # main
    frm11 = ttk.Frame(wnd)
    frm11.pack(fill=tk.BOTH, expand=tk.YES)
    if True:
      frm21 = ttk.LabelFrame(frm11, text="Typeface")
      frm21.pack(side=tk.TOP, fill=tk.X)
      if True:
        ttk.Label(frm21, text="font:").pack(padx=LABEL_PADX, side=tk.LEFT)

        font_names = [ft for ft in os.listdir(FONTSET_PATH) if path.isdir(path.join(FONTSET_PATH, ft))]
        var = tk.StringVar(wnd, TYPEFACE_DEFAULT['font'])
        self.var_font = var
        ttk.Combobox(frm21, values=font_names, state='readonly', width=COMBOBOX_WIDTH,
                      justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)

        ttk.Label(frm21, text="size:").pack(padx=LABEL_PADX, side=tk.LEFT)
        
        var = tk.IntVar(wnd, TYPEFACE_DEFAULT['size'])
        self.var_size = var
        tk.Spinbox(frm21, from_=5, to=15, increment=1, state='readonly', width=SPINBOX_WIDTH,
                    justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)

        ttk.Label(frm21, text="clarity:").pack(padx=LABEL_PADX, side=tk.LEFT)
        
        var = tk.IntVar(wnd, TYPEFACE_DEFAULT['clarity'])
        self.var_clarity = var
        tk.Spinbox(frm21, from_=-5, to=5, increment=1, state='readonly', width=SPINBOX_WIDTH,
                    justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)
        
        ttk.Label(frm21, text="italic:").pack(padx=LABEL_PADX, side=tk.LEFT)
        
        var = tk.BooleanVar(wnd, TYPEFACE_DEFAULT['italic'])
        self.var_italic = var
        ttk.Checkbutton(frm21, variable=var).pack(side=tk.LEFT)
      
        ttk.Label(frm21, text="color:").pack(padx=LABEL_PADX, side=tk.LEFT)
        
        self.var_color = TYPEFACE_DEFAULT['color']   # de facto, this is NOT tk.Variable, but 3-tuple (R, G, B)
        var = tk.StringVar(wnd, "(default)")
        self.var_color_text = var
        lb = ttk.Label(frm21, textvariable=var, justify=tk.CENTER, width=COLORSEL_WIDTH)
        lb.bind('<Button-1>', lambda evt: self._ctl_lb_hue_('choose'))
        lb.bind('<Button-3>', lambda evt: self._ctl_lb_hue_('clear'))
        lb.pack(side=tk.LEFT, fill=tk.X, expand=tk.NO)
        self._lb_color_bg_default = lb['background']  # save default bg color
        self.lb_color = lb

        ttk.Label(frm21, text="char spacing:").pack(padx=LABEL_PADX, side=tk.LEFT)
        
        var = tk.IntVar(wnd, TYPEFACE_DEFAULT['char_spacing'])
        self.var_char_spacing = var
        tk.Spinbox(frm21, from_=-5, to=5, increment=1, state='readonly', width=SPINBOX_WIDTH,
                    justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)

        ttk.Label(frm21, text="line spacing:").pack(padx=LABEL_PADX, side=tk.LEFT)
        
        var = tk.IntVar(wnd, TYPEFACE_DEFAULT['line_spacing'])
        self.var_line_spacing = var
        tk.Spinbox(frm21, from_=-5, to=5, increment=1, state='readonly', width=SPINBOX_WIDTH,
                    justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)
        
        ttk.Label(frm21, text="hw ratio:").pack(padx=LABEL_PADX, side=tk.LEFT)
        
        var = tk.DoubleVar(wnd, TYPEFACE_DEFAULT['hw_ratio'])
        self.var_hw_ratio = var
        tk.Spinbox(frm21, from_=0.5, to=1.5, increment=0.1, state='readonly', width=SPINBOX_WIDTH,
                    justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)

      # mid
      frm22 = ttk.LabelFrame(frm11, text="Viewer")
      frm22.bind('<Button-3>', lambda evt: self.menu.post(evt.x_root, evt.y_root))
      frm22.pack(fill=tk.BOTH, expand=tk.YES)
      if True:
        lb = ttk.Label(frm22)
        lb.bind('<Button-3>', lambda evt: self.menu.post(evt.x_root, evt.y_root))
        lb.pack(fill=tk.BOTH)
        self.viewer = lb
        self._save_filename_default = ''

      # bottom
      frm23 = ttk.LabelFrame(frm11, text="Editor (Press Ctrl+R/Enter to quickly refresh Viewer)")
      frm23.pack(side=tk.BOTTOM, fill=tk.X)
      if True:
        tx = tk.Text(frm23, font=tkfont.Font(family=EDITOR_FONT[0], size=EDITOR_FONT[1]),
                     undo=True, maxundo=50, height=EDITOR_LINES)
        tx.bind('<Control-Key-r>', lambda evt: self.view())
        tx.bind('<Control-Key-Return>', lambda evt: self.view())
        tx.pack(fill=tk.BOTH, expand=tk.YES)
        tx.focus_set()  # activate focus
        self.editor = tx

  def _ctl_lb_hue_(self, what='choose'):
    def high_contrast_bw_hexstr(rgb):
      def rgb2grey(rgb) -> int:
        # ITU-R 601-2 luma transform
        r, g, b = [float(x) for x in rgb]
        return (r * 299 + g * 587 + b * 114) // 1000
      return rgb2grey(rgb) <= 192 and '#FFFFFF' or '#000000'

    if what == 'choose':
      rgb, hexstr = colorchooser.askcolor()
      if not rgb or not hexstr: return
    
      self.var_color = tuple(round(x) for x in rgb)
      self.var_color_text.set(hexstr)
      self.lb_color.config(background=hexstr, foreground=high_contrast_bw_hexstr(rgb))
    elif what == 'clear':
      self.var_color = None
      self.var_color_text.set("(default)")
      self.lb_color.config(background=self._lb_color_bg_default, foreground='#000000')

  def view(self):
    text = self.editor.get('0.0', tk.END).strip()
    if text:
      self._save_filename_default = text.split('\n')[0]   # first line as save filename
      configs = {
        'font': self.var_font.get(),
        'size': self.var_size.get(),
        'clarity': self.var_clarity.get(),
        'color': self.var_color,
        'italic': self.var_italic.get(),
        'char_spacing': self.var_char_spacing.get(),
        'line_spacing': self.var_line_spacing.get(),
        'hw_ratio': self.var_hw_ratio.get(),
      }
      img = self.typesetter.print(text, **configs)
      imgtk = ImageTk.PhotoImage(img)   # fucking wrapper fo tkinter
      self.viewer.img = img
      self.viewer.imgtk = imgtk         # fuck the reference bug of GC
      self.viewer.config(image=imgtk)
    else:
      self._save_filename_default = ''
      self.viewer.img = None
      self.viewer.imgtk = None
      self.viewer.config(image=None)

  def save(self, how='default'):
    fn = self._save_filename_default + '.png'
    img = getattr(self.viewer, 'img', None)
    if not fn[:-4] or not img: return

    fp = path.join(OUT_PATH, fn)
    print(OUT_PATH)
    if how == 'select':
      fp = filedialog.asksaveasfilename(initialdir=OUT_PATH, initialfile=fn, 
                                        defaultextension='.png', filetypes=['png {.png}'])
      if not fp: return
    img.save(fp)
    logging.info('[Save] %r' % fp)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')
  App()
