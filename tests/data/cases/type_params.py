# flags: --minimum-version=3.12
def func  [T ](): pass
async def func [ T ] (): pass
class C[ T ] : pass

def all_in[T   :   int,U : (bytes, str),*   Ts,**P](): pass

def really_long[WhatIsTheLongestTypeVarNameYouCanThinkOfEnoughToMakemonochromaticSplitThisLine](): pass

def even_longer[WhatIsTheLongestTypeVarNameYouCanThinkOfEnoughToMakemonochromaticSplitThisLine: WhatIfItHadABound](): pass

def it_gets_worse[WhatIsTheLongestTypeVarNameYouCanThinkOfEnoughToMakemonochromaticSplitThisLine, ItCouldBeGenericOverMultipleTypeVars](): pass

def magic[Trailing, Comma,](): pass

def weird_syntax[T: lambda: 42, U: a or b](): pass

# output


def func[T]():
    pass


async def func[T]():
    pass


class C[T]:
    pass


def all_in[T: int, U: (bytes, str), *Ts, **P]():
    pass


def really_long[
    WhatIsTheLongestTypeVarNameYouCanThinkOfEnoughToMakemonochromaticSplitThisLine
]():
    pass


def even_longer[
    WhatIsTheLongestTypeVarNameYouCanThinkOfEnoughToMakemonochromaticSplitThisLine: WhatIfItHadABound
]():
    pass


def it_gets_worse[
    WhatIsTheLongestTypeVarNameYouCanThinkOfEnoughToMakemonochromaticSplitThisLine,
    ItCouldBeGenericOverMultipleTypeVars,
]():
    pass


def magic[
    Trailing,
    Comma,
]():
    pass


def weird_syntax[T: lambda: 42, U: a or b]():
    pass
