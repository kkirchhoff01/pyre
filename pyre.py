#!/usr/bin/python
import random
import sys
import curses
import time
import getopt

# Audio support
pyaudio_available = False
pygame_available = False
try:
  from pygame import mixer
  from pygame.mixer import music
  pygame_available = True
except ImportError:
  pygame_available = False
  try:
    import pyaudio
    import wave
    import threading
    pyaudio_available = True
  except ImportError:
    pyaudio_available = False

class Fire(object):
  MAX_INTENSITY = 100
  NUM_PARTICLES = 5
  NUM_COLORS = 30

  def __init__(self, settings):
    self.speed = int(settings['-r']) if '-r' in settings else 20
    self.scale = float(settings['-s']) if '-s' in settings else 1.0
    self.screen = curses.initscr()
    self.START_INTENSITY = int(settings['-i']) if '-i' in settings else self.MAX_INTENSITY
    self.START_OFFSET = int(settings['-w']) if '-w' in settings else 0
    self.START_HEIGHT = int(settings['-h']) if '-h' in settings else 0
    self.screen.clear()
    self.screen.nodelay(1)

    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    for i in range(0, curses.COLORS):
      curses.init_pair(i, i, -1)

    def color(r, g, b):
      return (16+r//48*36+g//48*6+b//48)
    self.heat = [color(16 * i,0,0) for i in range(0,16)] + [color(255,16 * i,0) for i in range(0,16)]
    self.particles = [ord(i) for i in (' ', '.', '*', '#', '@')]
    assert(len(self.particles) == self.NUM_PARTICLES)

    self.resize()
    self.volume = 1.0
    if pygame_available:
      mixer.init()
      music.load('fire.wav')
      music.play(-1)
    elif pyaudio_available:
      self.loop = True
      self.lock = threading.Lock()
      t = threading.Thread(target=self.play_fire)
      t.start()

  def play_fire(self):
    CHUNK = 1024
    p = pyaudio.PyAudio()
    wf = wave.open('fire.wav', 'rb')
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
              channels=wf.getnchannels(),
              rate=wf.getframerate(),
              output=True)
    loop = True
    while loop:
      self.lock.acquire()
      loop = self.loop
      self.lock.release()
      data = wf.readframes(CHUNK)
      if (len(data) == 0): wf.rewind()
      if (len(data) < 0): break
      stream.write(data)
    stream.stop_stream()
    stream.close()
    p.terminate()

  def shutdown(self):
    if pyaudio_available:
      self.lock.acquire()
      self.loop = False
      self.lock.release()

  def resize(self):
    self.height, self.width = self.screen.getmaxyx()[:2]
    self.prev_fire = [[0 for i in range(self.width - 1)] for j in range(self.height-1)]

  # Returns the intensity of the cell in the previous iteration
  def intensity(self, i, j):
    if (i < self.START_HEIGHT - 1): return 0
    if (i == self.START_HEIGHT - 1):
      if (self.START_OFFSET > j) or (self.width - self.START_OFFSET < j):
        return 0
      else:
        return self.START_INTENSITY
    if (j < 0): return 0
    if (j >= self.width - 1): return 0
    return min(self.prev_fire[i][j], self.MAX_INTENSITY)

  # The intensity is calculated by considering the row preceding
  # the current one in the previous time step.
  def get_intensity(self, i, j):
    prev_intensity = self.intensity(i - 1, j) + self.intensity(i - 1, j + 1) + self.intensity(i - 1, j - 1)
    fade = (i - self.START_HEIGHT + 1) ** 0.3 if i >= self.START_HEIGHT else 1
    new_intensity = random.randint(prev_intensity // 2, prev_intensity) / fade * self.scale
    return min(int(new_intensity), self.MAX_INTENSITY)

  def get_particle(self, intensity):
    index = int(intensity * self.NUM_PARTICLES / self.MAX_INTENSITY)
    index = min(index, self.NUM_PARTICLES - 1)
    return self.particles[index]

  def get_color(self, intensity):
    index = int(intensity * self.NUM_COLORS / self.MAX_INTENSITY)
    index = min(index, self.NUM_COLORS - 1)
    return curses.color_pair(self.heat[index])

  def redraw(self):
    for i in range(self.height - 1):
      for j in range(self.width - 1):
        # Figure out what to draw
        intensity = self.get_intensity(i, j)
        particle = self.get_particle(intensity)
        color = self.get_color(intensity)
        # Where to draw it
        x, y = j, self.height - i - 1
        self.screen.addch(y, x, particle, color)
        self.prev_fire[i][j] = int(intensity)
        # Save for the next iteration
    ch = self.screen.getch()
    if ch != curses.ERR:
      if pygame_available:
          if ch == ord('-') and self.volume != 0.0:
            self.volume = self.volume - .10
            music.set_volume(self.volume)
          elif ch == ord('+') or ch == ord('=') and self.volume != 1.0:
            self.volume = self.volume + .10
            music.set_volume(self.volume)
      if ch == ord('q') or ch == curses.KEY_ESCAPE:
        end_session(0)
    self.screen.refresh()
    self.screen.timeout(50)
    time.sleep(1.0 / self.speed)

  def end_session(self, exit_sig):
    if fire:
      fire.shutdown()
    curses.endwin()
    sys.exit(exit_sig)
    
if __name__ == "__main__":
  optlist, args = getopt.getopt(sys.argv[1:], 's:r:i:w:h:')
  fire = Fire(dict(optlist))
  try:
    while 1: 
      fire.redraw()
  except KeyboardInterrupt:
    fire.end_session(0)
  except:
    fire.end_session(1)
