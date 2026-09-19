# gg — ブロックから使うゲーム層。Python は論理だけを持ち、画素には触らない。
# JS が 1/60 秒ごとに _frame(keys) を呼び、戻り値の配列を描く。
import array as _ar

_IMG = {}
W = 360
H = 480
score = 0

_keys = 0
_sprites = []
_groups = []
_loop = None
_stop = 0
_msg = ''
_buf = _ar.array('f', [0.0] * 4)

_K = {'left': 1, 'right': 2, 'up': 4, 'down': 8, 'fire': 16}


def key(name):
    """いま押されているか。left right up down fire"""
    return (_keys & _K.get(name, 0)) != 0


def stop(msg=''):
    """ゲームを終える"""
    global _stop, _msg
    _stop = 1
    _msg = str(msg)


def loop(f):
    """1/60 秒ごとに呼ばれる関数を1つだけ登録する"""
    global _loop
    if _loop is not None:
        raise RuntimeError('gg.loop は1つだけ')
    _loop = f
    return f


class Sprite(object):
    def __init__(self, img, x=0, y=0, r=16):
        self.i = _IMG.get(img, 0)
        self.x = float(x)
        self.y = float(y)
        self.angle = 0.0
        self.frame = 0
        self.visible = True
        self.r = float(r)
        _sprites.append(self)

    def clamp(self, pad=0):
        """画面の中に収める"""
        if self.x < pad: self.x = pad
        if self.x > W - pad: self.x = W - pad
        if self.y < pad: self.y = pad
        if self.y > H - pad: self.y = H - pad

    def hit(self, other, r=None):
        d = self.r + (other.r if r is None else r)
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy < d * d


class Group(object):
    def __init__(self, img, r=8):
        self.i = _IMG.get(img, 0)
        self.r = float(r)
        self.xs = []
        self.ys = []
        self.vxs = []
        self.vys = []
        _groups.append(self)

    def add(self, x, y, vx=0.0, vy=0.0):
        self.xs.append(float(x))
        self.ys.append(float(y))
        self.vxs.append(float(vx))
        self.vys.append(float(vy))

    def move(self):
        xs, ys, vxs, vys = self.xs, self.ys, self.vxs, self.vys
        for k in range(len(xs)):
            xs[k] += vxs[k]
            ys[k] += vys[k]

    def cull(self, pad=40):
        """画面の外へ出たものを消す"""
        xs, ys, vxs, vys = self.xs, self.ys, self.vxs, self.vys
        i = 0
        n = len(xs)
        while i < n:
            if -pad <= xs[i] <= W + pad and -pad <= ys[i] <= H + pad:
                i += 1
            else:
                xs.pop(i); ys.pop(i); vxs.pop(i); vys.pop(i)
                n -= 1

    def hit(self, sp, r=None):
        """sp に当たったものを消して True を返す"""
        d = self.r + (sp.r if r is None else r)
        dd = d * d
        xs, ys = self.xs, self.ys
        for k in range(len(xs)):
            dx = xs[k] - sp.x
            dy = ys[k] - sp.y
            if dx * dx + dy * dy < dd:
                self.xs.pop(k); self.ys.pop(k)
                self.vxs.pop(k); self.vys.pop(k)
                return True
        return False

    def clear(self):
        del self.xs[:]; del self.ys[:]; del self.vxs[:]; del self.vys[:]

    @property
    def count(self):
        return len(self.xs)


def _need(n):
    global _buf
    want = 4 + n * 5
    if len(_buf) != want:
        _buf = _ar.array('f', [0.0] * want)
    return _buf


def _frame(keys):
    """JS が毎フレーム呼ぶ。戻り値: [n, stop, score, 0] + [img,x,y,angle,frame]*n"""
    global _keys
    _keys = keys
    if _loop is not None and not _stop:
        _loop()
    n = 0
    for s in _sprites:
        if s.visible:
            n += 1
    for g in _groups:
        n += len(g.xs)
    b = _need(n)
    b[0] = n
    b[1] = _stop
    b[2] = score
    b[3] = 0.0
    j = 4
    for s in _sprites:
        if not s.visible:
            continue
        b[j] = s.i; b[j+1] = s.x; b[j+2] = s.y; b[j+3] = s.angle; b[j+4] = s.frame
        j += 5
    for g in _groups:
        gi = g.i
        xs, ys = g.xs, g.ys
        for k in range(len(xs)):
            b[j] = gi; b[j+1] = xs[k]; b[j+2] = ys[k]; b[j+3] = 0.0; b[j+4] = 0.0
            j += 5
    return b
