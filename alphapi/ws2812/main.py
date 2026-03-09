"""Animated WS2812 ring demo for MicroPython.

Copy this file to your board (e.g. as main.py) and reboot to run the loop.
"""
from machine import Pin
import neopixel
import time
import math
import urandom

PIXEL_COUNT = 32
PIN_NO = 5  # D1 on many ESP8266/ESP32 boards; adjust if needed.
BRIGHTNESS = 0.25  # Keep modest to avoid brown-outs.


def wheel(pos):
    """Generate color tuples across a color wheel."""
    pos &= 255
    if pos < 85:
        return 255 - pos * 3, pos * 3, 0
    if pos < 170:
        pos -= 85
        return 0, 255 - pos * 3, pos * 3
    pos -= 170
    return pos * 3, 0, 255 - pos * 3


class WS2812Ring:
    def __init__(self, pin_no=PIN_NO, count=PIXEL_COUNT, brightness=BRIGHTNESS):
        self.count = count
        self.brightness = brightness
        self.strip = neopixel.NeoPixel(Pin(pin_no, Pin.OUT), count)

    def _scale(self, color):
        return tuple(int(c * self.brightness) for c in color)

    def clear(self):
        for i in range(self.count):
            self.strip[i] = (0, 0, 0)
        self.strip.write()

    def rainbow_cycle(self, reps=2, wait_ms=2):
        for j in range(256 * reps):
            for i in range(self.count):
                idx = (i * 256 // self.count + j) & 255
                self.strip[i] = self._scale(wheel(idx))
            self.strip.write()
            time.sleep_ms(wait_ms)

    def comet(self, color=(0, 180, 255), tail=10, laps=6, wait_ms=25):
        decay = [(tail - i) / tail for i in range(tail)]
        for lap in range(self.count * laps):
            for i in range(self.count):
                self.strip[i] = (0, 0, 0)
            for seg in range(tail):
                pos = (lap - seg) % self.count
                scaled = tuple(int(color[c] * decay[seg] * self.brightness) for c in range(3))
                self.strip[pos] = scaled
            self.strip.write()
            time.sleep_ms(wait_ms)

    def sparkle(self, base=(20, 0, 60), sparkle_color=(120, 120, 120), flashes=180, wait_ms=35):
        base_scaled = self._scale(base)
        for _ in range(flashes):
            for i in range(self.count):
                self.strip[i] = base_scaled
            idx = time.ticks_ms() % self.count
            self.strip[idx] = self._scale(sparkle_color)
            self.strip.write()
            time.sleep_ms(wait_ms)

    def breathing(self, color=(255, 40, 5), cycles=3, period_ms=2000):
        start = time.ticks_ms()
        duration = cycles * period_ms
        while time.ticks_diff(time.ticks_ms(), start) < duration:
            phase = time.ticks_diff(time.ticks_ms(), start) % period_ms
            level = (1 - math.cos(phase / period_ms * 2 * math.pi)) * 0.5
            scaled = tuple(int(c * level * self.brightness) for c in color)
            for i in range(self.count):
                self.strip[i] = scaled
            self.strip.write()
            time.sleep_ms(20)

    def rain(self, color=(0, 70, 255), drops=220, decay=0.78, chance=0.35, wait_ms=35):
        # Random droplets that fade like rainfall around the ring.
        levels = [0.0] * self.count
        threshold = int(255 * chance)
        for _ in range(drops):
            if urandom.getrandbits(8) < threshold:
                idx = urandom.getrandbits(8) % self.count
                levels[idx] = 1.0
            for i in range(self.count):
                levels[i] *= decay
                if levels[i] < 0.02:
                    levels[i] = 0.0
                self.strip[i] = tuple(int(color[c] * levels[i] * self.brightness) for c in range(3))
            self.strip.write()
            time.sleep_ms(wait_ms)

    def heartbeat(self, color=(255, 0, 80), beats=8, period_ms=900):
        # Envelope mimics the quick double-pulse of a heartbeat.
        profile = (
            (0.00, 0.05),
            (0.15, 1.0),
            (0.25, 0.2),
            (0.35, 0.7),
            (0.45, 0.15),
            (1.00, 0.05),
        )
        for _ in range(beats):
            start = time.ticks_ms()
            end_time = start + period_ms
            while time.ticks_diff(end_time, time.ticks_ms()) > 0:
                elapsed = time.ticks_diff(time.ticks_ms(), start)
                phase = max(0.0, min(1.0, elapsed / period_ms))
                for idx in range(len(profile) - 1):
                    t0, v0 = profile[idx]
                    t1, v1 = profile[idx + 1]
                    if t0 <= phase <= t1:
                        blend = (phase - t0) / (t1 - t0 or 1)
                        level = v0 + (v1 - v0) * blend
                        break
                else:
                    level = profile[-1][1]
                scaled = tuple(int(c * level * self.brightness) for c in color)
                for i in range(self.count):
                    self.strip[i] = scaled
                self.strip.write()
                time.sleep_ms(20)

    def musical_notes(
        self,
        palette=None,
        duration_ms=7000,
        wait_ms=35,
        lifespan=18,
        max_notes=5,
    ):
        # Energetic blobs that bounce around like jittery music notes.
        if palette is None:
            palette = (
                (255, 200, 40),
                (0, 255, 140),
                (150, 120, 255),
            )
        notes = []  # Each note is [pos, velocity, age, color, direction].
        steps = max(1, duration_ms // wait_ms)
        spawn_threshold = 90  # ~35% chance per frame when below max_notes.

        for _ in range(steps):
            if len(notes) < max_notes and urandom.getrandbits(8) < spawn_threshold:
                notes.append(
                    [
                        urandom.getrandbits(8) % self.count,
                        1 + (urandom.getrandbits(2) & 1),
                        0,
                        palette[urandom.getrandbits(8) % len(palette)],
                        1 if urandom.getrandbits(1) else -1,
                    ]
                )

            frame = [[0, 0, 0] for _ in range(self.count)]
            pruned = []
            for note in notes:
                note[0] = (note[0] + note[1] * note[4]) % self.count
                if urandom.getrandbits(3) == 0:
                    note[4] *= -1  # Flip direction occasionally to mimic jumps.
                note[2] += 1
                if note[2] >= lifespan:
                    continue
                intensity = 1 - note[2] / lifespan
                # Ease curve makes the pop sharper at the start.
                intensity = intensity * intensity
                scaled = tuple(int(ch * intensity * self.brightness) for ch in note[3])
                idx = int(note[0])
                neighbor = (idx + note[4]) % self.count
                halo = tuple(int(val * 0.45) for val in scaled)
                for ch in range(3):
                    frame[idx][ch] = min(255, frame[idx][ch] + scaled[ch])
                    frame[neighbor][ch] = min(255, frame[neighbor][ch] + halo[ch])
                pruned.append(note)

            notes = pruned
            for px in range(self.count):
                self.strip[px] = tuple(frame[px])
            self.strip.write()
            time.sleep_ms(wait_ms)

    def snake(
        self,
        body_color=(0, 255, 80),
        food_color=(255, 100, 20),
        rounds=8,
        wait_ms=85,
        grow_limit=18,
    ):
        # Classic snake chase wrapped around the ring with glowing body.
        length = 5
        snake = [0]
        direction = 1

        def pick_food():
            for _ in range(20):
                cand = urandom.getrandbits(8) % self.count
                if cand not in snake:
                    return cand
            return (snake[-1] + 3) % self.count

        food = pick_food()
        total_steps = max(1, rounds * self.count)
        for _ in range(total_steps):
            head = (snake[0] + direction) % self.count
            if head in snake:
                direction *= -1
                head = (snake[0] + direction) % self.count
            snake.insert(0, head)

            if head == food and length < grow_limit:
                length += 1
                food = pick_food()

            if len(snake) > length:
                snake.pop()

            if urandom.getrandbits(4) == 0:
                direction *= -1

            for i in range(self.count):
                self.strip[i] = (0, 0, 0)

            for idx, pos in enumerate(snake):
                falloff = 1 - idx / max(1, len(snake)) * 0.6
                scaled = tuple(int(body_color[c] * falloff * self.brightness) for c in range(3))
                self.strip[pos] = scaled

            self.strip[food] = self._scale(food_color)
            self.strip.write()
            time.sleep_ms(wait_ms)


def main():
    ring = WS2812Ring()
    try:
        while True:
            ring.rainbow_cycle()
            ring.comet()
            ring.sparkle()
            ring.breathing()
            ring.rain()
            ring.musical_notes()
            ring.snake()
            ring.heartbeat()
    except KeyboardInterrupt:
        ring.clear()


if __name__ == "__main__":
    main()
