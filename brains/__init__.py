from .base import Brain,summarize,kind_of
from .acp import Acp,GrokAcp
from .claude import Claude
KINDS={"grok":GrokAcp,"claude":Claude,"acp-stdio":Acp}
def make(kind,cfg):return KINDS[kind](cfg)
def available(cfg):return [dict(kind=k,**c.probe(cfg)) for k,c in KINDS.items()]
