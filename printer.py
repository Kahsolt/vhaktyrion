#!/usr/bin/env python3
# Author: Armit
# Create time: 2019/09/27 
# Update time: 2019/10/02

import sys, os
from os import path
import logging
import re
import gzip
from functools import reduce
import pickle
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from tkinter import filedialog
from tkinter import colorchooser

__version__ = '0.1'

TYPEFACE_DEFAULT = {
  'font': 'sculpture',
  'size': 12,
  'clarity': 0,
  'color': None,
  'italic': False,
  'raw_input': False,
  'symbol_spacing': 0,
  'line_spacing': 0,
  'hw_ratio': 1.0,
}

BASE_PATH = path.dirname(path.abspath(__file__))
DEFAULT_SAVE_PATH = path.join(BASE_PATH, 'out', 'text.png')
FONTSET_PATH = path.join(BASE_PATH, 'fonts')
FONT_CACHE_FILE = 'fonts.pkl'
LABEL_PADX = 10
WINDOW_SIZE = (800, 600)  # (1024, 768)
EDITOR_LINES = 8          # 12
EDITOR_FONT = ('Times New Roman', 14)
ZIPMOD = gzip

class Utils:
 
  @staticmethod
  def rgb2grey(rgb) -> int:
    # ITU-R 601-2 luma transform
    r, g, b = [float(x) for x in rgb]
    return (r * 299 + g * 587 + b * 114) // 1000

  @staticmethod
  def rgb2hexstr(rgb) -> str:
    r, g, b = [int(x) for x in rgb]
    return '#' + hex((r << 16) + (g << 8) + (b))[2:].rjust(6, '0')

  @staticmethod
  def high_contrast_bw_hexstr(rgb):
    return Utils.rgb2grey(rgb) <= 192 and '#FFFFFF' or '#000000'


class Translater:

  INSTANCE = None

  def __new__(cls, *args, **kwargs):
    if not cls.INSTANCE:
      cls.INSTANCE = super().__new__(cls, *args, **kwargs)
    return cls.INSTANCE

  def latinization_to_letters(self, latinization) -> list:
    return [x for x in latinization]

  def phonemes_to_letters(self, phonemes) -> list:
    return [x for x in phonemes]


class FontLibrary:

  INSTANCE = None
  FONTS = { }     # { 'name': { 'a': Image } }

  def __new__(cls, *args, **kwargs):
    if not cls.INSTANCE:
      cls.INSTANCE = super().__new__(cls, *args, **kwargs)
    return cls.INSTANCE

  @classmethod
  def get(cls, name) -> dict:
    cache_pkl = path.join(BASE_PATH, FONT_CACHE_FILE)
    if not cls.FONTS:
      if path.exists(cache_pkl):
        logging.info('[%s] loading from font cache' % cls.__name__)
        with ZIPMOD.open(cache_pkl, 'rb') as fp:
          cls.FONTS = pickle.load(fp)
        logging.info('[%s] %d fonts loaded' % (cls.__name__, len(cls.FONTS)))

    if name not in cls.FONTS:
      logging.info('[%s] building fontcache for %r' % (cls.__name__, name))
      
      fontset = { }
      dp = path.join(FONTSET_PATH, name)
      for fn in os.listdir(dp):
        letter_name = path.splitext(fn)[0]
        fontset[letter_name] = Image.open(path.join(dp, fn)).convert('L')
      cls.FONTS[name] = fontset

      with ZIPMOD.open(cache_pkl, 'wb+') as fp:
        pickle.dump(cls.FONTS, fp, protocol=4)
    return cls.FONTS.get(name)


class Typesetter:

  class Letter:

    def __init__(self, margin=(2, 0)):
      self.body = None
      self.nota_upper = None
      self.nota_lower = None
      self.margin = margin   # (up/down, left, right)

    def width(self): return 0
    def height(self): return 0

  class Line:

    def __init__(self, margin=(2, 2)):
      self.letters = [ ]
      self.margin = margin

    def add(self, letter):
      self.letters.append(letter)

    def width(self): return 0
    def height(self): return 0

  class Text:

    def __init__(self, margin=(6, 4)):
      self.lines = [ ]
      self.margin = margin
    
    def add(self, line):
      self.lines.append(line)
    
    def width(self): return 0
    def height(self): return 0
  
  INSTANCE = None

  def __new__(cls, *args, **kwargs):
    if not cls.INSTANCE:
      cls.INSTANCE = super().__new__(cls, *args, **kwargs)
    return cls.INSTANCE

  def __init__(self):
    self.translater = Translater()

  def print(self, text, **configs):
    tx = self.Text()
    for line in text.split('\n'):
      ln = self.Line()
      for letter in line:
        let = self.Letter(letter)
        ln.add(let)
      tx.add(ln)
    
    letters = self.translater.latinization_to_letters(text)
    fontset = FontLibrary.get(configs.get('font') or TYPEFACE_DEFAULT['font'])
    let_imgs = [fontset.get(let) for let in letters]
    print(let_imgs)
    W = reduce(lambda w, img: w + img.width, let_imgs, 0)
    H = reduce(lambda h, img: max(h, img.height), let_imgs, 0)
    out = Image.new('L', (W, H))
    print('(W, H): %d, %d' % (W, H))
    w = 0
    for let in let_imgs:
      box = (w, 0)
      out.paste(let, box)
      w += let.width
    print(out)
    return out


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
    menu.add_command(label="Save..", command=lambda: self.save('select'))
    # wnd.config(menu=menu)
    self.menu = menu

    # main
    frm11 = ttk.Frame(wnd)
    frm11.pack(fill=tk.BOTH, expand=tk.YES)
    if True:
      frm21 = ttk.LabelFrame(frm11, text="Typeface")
      frm21.pack(side=tk.TOP, fill=tk.X)
      if True:
        # row 1: font
        frm31 = ttk.Frame(frm21)
        frm31.pack(side=tk.TOP, fill=tk.X)
        if True:
          ttk.Label(frm31, text="font:").pack(padx=LABEL_PADX, side=tk.LEFT)

          var = tk.StringVar(wnd, TYPEFACE_DEFAULT['font'])
          self.var_font = var
          ttk.Combobox(frm31, values=os.listdir(FONTSET_PATH),
                       justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)

          ttk.Label(frm31, text="size:").pack(padx=LABEL_PADX, side=tk.LEFT)
          
          var = tk.IntVar(wnd, TYPEFACE_DEFAULT['size'])
          self.var_size = var
          tk.Spinbox(frm31, from_=8, to=24, increment=1,
                     justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)

          ttk.Label(frm31, text="clarity:").pack(padx=LABEL_PADX, side=tk.LEFT)
          
          var = tk.IntVar(wnd, TYPEFACE_DEFAULT['clarity'])
          self.var_clarity = var
          tk.Spinbox(frm31, from_=-10, to=10, increment=1,
                     justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)

          ttk.Label(frm31, text="color:").pack(padx=LABEL_PADX, side=tk.LEFT)
          
          self.var_color = TYPEFACE_DEFAULT['color']   # de facto, this is NOT tk.Variable, but 3-tuple (R, G, B)
          var = tk.StringVar(wnd, "not selected")
          self.var_color_text = var
          lb = ttk.Label(frm31, textvariable=var, anchor=tk.CENTER)
          lb.bind('<Button-1>', lambda evt: self._ctl_lb_hue_('choose'))
          lb.bind('<Button-3>', lambda evt: self._ctl_lb_hue_('clear'))
          lb.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)
          self._lb_color_bg_default = lb['background']  # save default bg color
          self.lb_color = lb

          ttk.Label(frm31, text="italic:").pack(padx=LABEL_PADX, side=tk.LEFT)
          
          var = tk.BooleanVar(wnd, TYPEFACE_DEFAULT['italic'])
          self.var_italic = var
          ttk.Checkbutton(frm31, variable=var).pack(side=tk.LEFT)

        # row 2: paragraph
        frm32 = ttk.Frame(frm21)
        frm32.pack(side=tk.TOP, fill=tk.X)
        if True:
          ttk.Label(frm32, text="symbol spacing:").pack(padx=LABEL_PADX, side=tk.LEFT)
          
          var = tk.IntVar(wnd, TYPEFACE_DEFAULT['symbol_spacing'])
          self.var_symbol_spacing = var
          tk.Spinbox(frm32, from_=-8, to=12, increment=1,
                     justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)

          ttk.Label(frm32, text="line spacing:").pack(padx=LABEL_PADX, side=tk.LEFT)
          
          var = tk.IntVar(wnd, TYPEFACE_DEFAULT['line_spacing'])
          self.var_line_spacing = var
          tk.Spinbox(frm32, from_=-8, to=12, increment=1,
                     justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)
          
          ttk.Label(frm32, text="hw ratio:").pack(padx=LABEL_PADX, side=tk.LEFT)
          
          var = tk.DoubleVar(wnd, TYPEFACE_DEFAULT['hw_ratio'])
          self.var_hw_ratio = var
          tk.Spinbox(frm32, from_=0.6, to=1.4, increment=0.1,
                     justify=tk.CENTER, textvariable=var).pack(side=tk.LEFT)

          ttk.Label(frm32, text="raw input:").pack(padx=LABEL_PADX, side=tk.LEFT)
          
          var = tk.BooleanVar(wnd, TYPEFACE_DEFAULT['raw_input'])
          self.var_raw_input = var
          ttk.Checkbutton(frm32, variable=var).pack(side=tk.LEFT)

      # mid
      frm22 = ttk.LabelFrame(frm11, text="Viewer")
      frm22.bind('<Button-3>', lambda evt: self.menu.post(evt.x_root, evt.y_root))
      frm22.pack(fill=tk.BOTH, expand=tk.YES)
      if True:
        lb = ttk.Label(frm22)
        lb.bind('<Button-3>', lambda evt: self.menu.post(evt.x_root, evt.y_root))
        lb.pack(fill=tk.BOTH)
        self.viewer = lb

      # bottom
      frm23 = ttk.LabelFrame(frm11, text="Editor (Press Ctrl+Enter to quick refresh Viewer)")
      frm23.pack(side=tk.BOTTOM, fill=tk.X)
      if True:
        tx = tk.Text(frm23, font=tkfont.Font(family=EDITOR_FONT[0], size=EDITOR_FONT[1]),
                     undo=True, maxundo=50, height=EDITOR_LINES)
        tx.bind('<Control-Key-Return>', lambda evt: self.view())
        tx.pack(fill=tk.BOTH, expand=tk.YES)
        tx.focus_set()
        self.editor = tx

  def _ctl_lb_hue_(self, what='choose'):
    if what == 'choose':
      rgb, hexstr = colorchooser.askcolor()
      if not rgb or not hex: return
    
      self.var_color = tuple(round(x) for x in rgb)
      self.var_color_text.set(hexstr)
      self.lb_color.config(background=hexstr, foreground=Utils.high_contrast_bw_hexstr(rgb))
    elif what == 'clear':
      self.var_color = None
      self.var_color_text.set("<not selected>")
      self.lb_color.config(background=self._lb_color_bg_default, foreground='#000000')

  def view(self):
    text = self.editor.get('0.0', tk.END).strip()
    configs = {
      'font': self.var_font.get(),
      'size': self.var_size.get(),
      'clarity': self.var_clarity.get(),
      'color': self.var_color,
      'italic': self.var_italic.get(),
      'raw_input': self.var_raw_input.get(),
      'symbol_spacing': self.var_symbol_spacing.get(),
      'line_spacing': self.var_line_spacing.get(),
      'hw_ratio': self.var_hw_ratio.get(),
    }
    img = self.typesetter.print(text, **configs)
    imgtk = ImageTk.PhotoImage(img)   # fucking wrapper fo tkinter
    self.viewer.img = img
    self.viewer.imgtk = imgtk         # fuck the reference bug of GC
    self.viewer.config(image=imgtk)

  def save(self, how='default'):
    if how == 'default':
      img = self.viewer.img
      if img:
        os.makedirs(path.dirname(DEFAULT_SAVE_PATH), exist_ok=True)
        img.save(DEFAULT_SAVE_PATH)
        logging.info('[Save] %r' % DEFAULT_SAVE_PATH)
    elif how == 'select':
      fp = filedialog.asksaveasfilename(defaultextension='.png')
      print(fp)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, 
                      format='%(asctime)s [%(levelname)s] - %(message)s')
  App()
