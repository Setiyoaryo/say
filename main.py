import os, sys, json, re, time, random
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import requests
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_abi import encode as abi_encode
from eth_utils import keccak, to_checksum_address
from hexbytes import HexBytes
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box
from rich.theme import Theme
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeRemainingColumn, TextColumn

theme = Theme({"title":"bold cyan","ok":"bold green","err":"bold red","warn":"bold yellow","muted":"grey66","accent":"magenta"})
console = Console(theme=theme)

load_dotenv()
RPC_URL = os.getenv("RPC_URL","https://testnet.dplabs-internal.com").strip()
EXPLORER_BASE = os.getenv("EXPLORER_BASE","https://testnet.pharosscan.xyz").rstrip("/")
CHAIN_ID = int(os.getenv("CHAIN_ID","688688"))
PRIVATE_KEY_ENV = os.getenv("PRIVATE_KEY","").strip()
WAIT_TIMEOUT_SECS = int(os.getenv("WAIT_TIMEOUT_SECS","600"))
TX_DELAY_JITTER_SECS = int(os.getenv("TX_DELAY_JITTER_SECS","30"))
MAX_PRIORITY_GWEI = int(os.getenv("MAX_PRIORITY_GWEI","2"))
FEE_BUMP_PCT = float(os.getenv("FEE_BUMP_PCT","0.20"))

CONFIG_PATH = "runner_config.json"
WALLETS_JSON = "wallets.json"
WALLETS_TXT = "wallets.txt"
PROXIES_TXT = "proxies.txt"

POOL_ADDRESS   = os.getenv("POOL_ADDRESS","0x11d1ca4012d94846962bca2FBD58e5A27ddcBfC5")
ASSET_USDC     = os.getenv("ASSET_USDC","")
ASSET_USDT     = os.getenv("ASSET_USDT","")
ASSET_WPHRS    = os.getenv("ASSET_WPHRS","")
ASSET_TSLA     = os.getenv("ASSET_TSLA","0xa778b48339d3c6b4bc5a75b37c6ce210797076b1")
ASSET_NVIDIA   = os.getenv("ASSET_NVIDIA","0xaaf3a7f1676385883593d7ea7ea4fccc675ee5d6")
ASSET_GOLD     = os.getenv("ASSET_GOLD","0xAaf03Cbb486201099EdD0a52E03Def18cd0c7354")
FAUCET_ADDRESS = os.getenv("FAUCET_ADDRESS","0x0e29d74af0489f4b08fbfc774e25c0d3b5f43285")
FAUCET_AMOUNT  = Decimal(os.getenv("FAUCET_AMOUNT","100"))

CONTROLLER  = os.getenv("CONTROLLER_ADDR", os.getenv("CONTROLLER","0x51bE1EF20a1fD5179419738FC71D95A8b6f8A175"))
RESOLVER    = os.getenv("RESOLVER_ADDR",   os.getenv("RESOLVER","0x9a43dcA1C3BB268546b98eB2AB1401bfC5B58505"))
TLD         = os.getenv("TLD","phrs")
EXTRA_WAIT  = int(os.getenv("COMMIT_EXTRA_WAIT_SEC","5"))
TIP_BPS     = int(os.getenv("TIP_BPS","200"))

R2USDC_ADDRESS    = "0x8bebfcbe5468f146533c182df3dfbf5ff9be00e2"
R2USD_ADDRESS     = "0x4f5b54d4af2568cefafa73bb062e5d734b55aa05"
ROUTER_ADDRESS    = "0x4f5b54d4AF2568cefafA73bB062e5d734b55AA05"
STAKING_CONTRACT  = "0xF8694d25947A0097CB2cea2Fc07b071Bdf72e1f8"
SEL_USDC_TO_R2USD = bytes.fromhex("095e7a95")
SEL_R2USD_TO_USDC = bytes.fromhex("9dc29fac")
SEL_STAKE         = bytes.fromhex("1a5f0f00")

BROKEX_USDT_ADDRESS         = "0x78ac5e2d8a78a8b8e6d10c7b7274b03c10c91cef"
BROKEX_TRADE_ROUTER_ADDRESS = "0x34f89ca5a1c6dc4eb67dfe0af5b621185df32854"
BROKEX_POOL_ROUTER_ADDRESS  = "0x9A88d07850723267DB386C681646217Af7e220d7"
BROKEX_PROOF_API            = "https://proof.brokex.trade/proof?pairs="
BROKEX_PAIRS = [{"name":"BTC_USDT","idx":0},{"name":"ETH_USDT","idx":1},{"name":"LINK_USDT","idx":2},{"name":"SOL_USDT","idx":10}]

TOKEN_ADDRESS_P5    = os.getenv("TOKEN_ADDRESS","0xD4071393f8716661958F766DF660033b3d35fD29")
DEPOSIT_CONTRACT_P5 = os.getenv("DEPOSIT_CONTRACT","0xA307cE75Bc6eF22794410D783e5D4265dEd1A24f")
DEPOSIT_AMOUNT_P5   = Decimal(os.getenv("DEPOSIT_AMOUNT","100"))
GAS_MULT_P5         = float(os.getenv("GAS_MULT","1.1"))
MAX_APPROVE_P5      = os.getenv("MAX_APPROVE","true").lower()=="true"

USDC_SP_ADDRESS   = os.getenv("USDC_ADDRESS","0x72df0bcd7276f2dFbAc900D1CE63c272C4BCcCED")
SPOUT_SPENDER     = os.getenv("SPOUT_SPENDER","0x81b33972f8bdf14fD7968aC99CAc59BcaB7f4E9A")
SPOUT_DEFAULT_AMT = Decimal(os.getenv("SPOUT_AMOUNT_DEFAULT","0.1"))
SPOUT_SLEEP_DEFAULT = int(os.getenv("SPOUT_SLEEP_SECONDS","60"))
APPROVE_AMOUNT_USDC = Decimal(os.getenv("SPOUT_APPROVE_AMOUNT","100"))

ERC20_ABI = [
    {"name":"allowance","type":"function","stateMutability":"view",
     "inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],
     "outputs":[{"name":"","type":"uint256"}]},
    {"name":"approve","type":"function","stateMutability":"nonpayable",
     "inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],
     "outputs":[{"name":"","type":"bool"}]},
    {"name":"balanceOf","type":"function","stateMutability":"view",
     "inputs":[{"name":"owner","type":"address"}],
     "outputs":[{"name":"","type":"uint256"}]},
    {"name":"decimals","type":"function","stateMutability":"view",
     "inputs":[],"outputs":[{"name":"","type":"uint8"}]},
    {"name":"symbol","type":"function","stateMutability":"view",
     "inputs":[],"outputs":[{"name":"","type":"string"}]},
    {"name":"transfer","type":"function","stateMutability":"nonpayable",
     "inputs":[{"name":"to","type":"address"},{"name":"value","type":"uint256"}],
     "outputs":[{"name":"","type":"bool"}]}
]

POOL_ABI = [
    {"inputs":[{"internalType":"address","name":"asset","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"address","name":"onBehalfOf","type":"address"},{"internalType":"uint16","name":"referralCode","type":"uint16"}],"name":"supply","outputs":[],"stateMutability":"nonpayable","type":"function"}
]
FAUCET_ABI = [
    {"inputs":[{"internalType":"address","name":"_asset","type":"address"},{"internalType":"address","name":"_account","type":"address"},{"internalType":"uint256","name":"_amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"}
]
CONTROLLER_ABI = [
  {"inputs":[{"internalType":"string","name":"name","type":"string"},{"internalType":"address","name":"owner","type":"address"},{"internalType":"uint256","name":"duration","type":"uint256"},{"internalType":"bytes32","name":"secret","type":"bytes32"},{"internalType":"address","name":"resolver","type":"address"},{"internalType":"bytes[]","name":"data","type":"bytes[]"},{"internalType":"bool","name":"reverseRecord","type":"bool"},{"internalType":"uint16","name":"ownerControlledFuses","type":"uint16"}],"name":"makeCommitment","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"pure","type":"function"},
  {"inputs":[{"internalType":"bytes32","name":"commitment","type":"bytes32"}],"name":"commit","outputs":[],"stateMutability":"nonpayable","type":"function"},
  {"inputs":[{"internalType":"string","name":"name","type":"string"},{"internalType":"uint256","name":"duration","type":"uint256"}],"name":"rentPrice","outputs":[{"components":[{"internalType":"uint256","name":"base","type":"uint256"},{"internalType":"uint256","name":"premium","type":"uint256"}],"internalType":"struct IPriceOracle.Price","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"string","name":"name","type":"string"}],"name":"available","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
  {"inputs":[],"name":"minCommitmentAge","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
  {"inputs":[{"internalType":"string","name":"name","type":"string"},{"internalType":"address","name":"owner","type":"address"},{"internalType":"uint256","name":"duration","type":"uint256"},{"internalType":"bytes32","name":"secret","type":"bytes32"},{"internalType":"address","name":"resolver","type":"address"},{"internalType":"bytes[]","name":"data","type":"bytes[]"},{"internalType":"bool","name":"reverseRecord","type":"bool"},{"internalType":"uint16","name":"ownerControlledFuses","type":"uint16"}],"name":"register","outputs":[],"stateMutability":"payable","type":"function"}
]
RESOLVER_ABI = [
  {"inputs":[{"internalType":"bytes32","name":"node","type":"bytes32"},{"internalType":"uint256","name":"coinType","type":"uint256"},{"internalType":"bytes","name":"a","type":"bytes"}],"name":"setAddr","outputs":[],"stateMutability":"nonpayable","type":"function"}
]
BROKEX_ABI = [{
    "name":"openPosition","type":"function","stateMutability":"nonpayable",
    "inputs":[{"internalType":"uint256","name":"idx","type":"uint256"},{"internalType":"bytes","name":"proof","type":"bytes"},{"internalType":"bool","name":"isLong","type":"bool"},{"internalType":"uint256","name":"lev","type":"uint256"},{"internalType":"uint256","name":"size","type":"uint256"},{"internalType":"uint256","name":"sl","type":"uint256"},{"internalType":"uint256","name":"tp","type":"uint256"}],
    "outputs":[{"internalType":"uint256","name":"","type":"uint256"}],
}]
DEPOSIT_ABI = [
    {"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"deposit","outputs":[],"stateMutability":"nonpayable","type":"function"}
]

MAX_UINT256 = (1<<256)-1

def fmt_addr(a: str) -> str:
    return f"{a[:6]}…{a[-4:]}"

def tx_link(h: str) -> str:
    return f"{EXPLORER_BASE}/tx/{h}"

def gwei(x: float) -> int:
    return int(Decimal(x) * Decimal(1_000_000_000))

def eip1559_supported(w3: Web3) -> bool:
    try:
        blk = w3.eth.get_block("latest")
        return "baseFeePerGas" in blk and blk["baseFeePerGas"] is not None
    except Exception:
        return False

def suggest_fees(w3: Web3, priority_gwei: int = MAX_PRIORITY_GWEI) -> Dict[str,int]:
    if eip1559_supported(w3):
        base = int(w3.eth.get_block("latest").get("baseFeePerGas", w3.eth.gas_price))
        prio = gwei(priority_gwei)
        return {"maxFeePerGas": base*2 + prio, "maxPriorityFeePerGas": prio}
    return {"gasPrice": int(w3.eth.gas_price)}

def build_tx_common(w3: Web3, sender: str, bump=False) -> Dict[str,Any]:
    fees = suggest_fees(w3)
    if bump and "gasPrice" in fees:
        fees["gasPrice"] = int(fees["gasPrice"]*(1+FEE_BUMP_PCT))
    if bump and "maxFeePerGas" in fees:
        fees["maxFeePerGas"] = int(fees["maxFeePerGas"]*(1+FEE_BUMP_PCT))
    return {"from": sender, "nonce": w3.eth.get_transaction_count(sender, "pending"), "chainId": CHAIN_ID, **fees}

def sign_send_wait(w3: Web3, tx: Dict[str,Any], pk: str, label="TX", gas_fallback=250_000) -> Tuple[bool, Optional[str]]:
    if "gas" not in tx:
        try:
            est = w3.eth.estimate_gas(dict(tx))
            tx["gas"] = int(est*1.2)
        except Exception:
            tx["gas"] = gas_fallback
    signed = w3.eth.account.sign_transaction(tx, private_key=pk)
    raw = getattr(signed,"rawTransaction",None) or getattr(signed,"raw_transaction",None)
    try:
        h = w3.eth.send_raw_transaction(raw)
    except Exception as e:
        console.print(f"[err]{label} gagal dikirim: {e}[/err]")
        return False, None
    hx = h.hex()
    console.print(f"[muted]Sent {label}[/muted]: {hx}")
    try:
        rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=WAIT_TIMEOUT_SECS)
    except Exception as e:
        console.print(f"[err]wait_for_receipt: {e}[/err]")
        return False, hx
    if rcpt.status == 1:
        console.print(f"[ok]{label} Mined[/ok] • block={rcpt.blockNumber} • gasUsed={rcpt.gasUsed}")
        return True, hx
    console.print(f"[err]{label} Reverted[/err] • block={rcpt.blockNumber}")
    return False, hx

def sleep_countdown(seconds: int, label="Jeda"):
    seconds = max(0, int(seconds))
    if seconds == 0:
        return
    with Progress(SpinnerColumn(style="accent"), TextColumn("[muted]{task.description}[/muted]"), BarColumn(bar_width=None), TimeRemainingColumn(), transient=True, console=console) as prog:
        t = prog.add_task(label, total=seconds)
        for _ in range(seconds):
            time.sleep(1)
            prog.advance(t, 1)

def to_units(amount: Decimal|float|str, decimals: int) -> int:
    return int(Decimal(str(amount)).scaleb(decimals))

def get_decimals(w3: Web3, token: str) -> int:
    c = w3.eth.contract(address=to_checksum_address(token), abi=ERC20_ABI)
    return int(c.functions.decimals().call())

def ensure_approval(w3: Web3, token: str, owner: str, spender: str, need: int, pk: str):
    c = w3.eth.contract(address=to_checksum_address(token), abi=ERC20_ABI)
    cur = int(c.functions.allowance(owner, to_checksum_address(spender)).call())
    if cur >= need:
        return
    tx = c.functions.approve(to_checksum_address(spender), MAX_UINT256).build_transaction({**build_tx_common(w3, owner), "gas": 120_000})
    ok, _ = sign_send_wait(w3, tx, pk, "approve", 120_000)
    if not ok:
        raise RuntimeError("Approve gagal")

def _keccak_text(s: str) -> bytes:
    try:
        return keccak(text=s)
    except TypeError:
        return keccak(s.encode("utf-8"))

def namehash(name: str) -> bytes:
    node = b"\x00"*32
    if name:
        for label in reversed(name.split(".")):
            node = keccak(node + _keccak_text(label))
    return node

def coin_type_for_chain(chain_id: int) -> int:
    return (1 << 31) | chain_id

def encode_setaddr_calldata(resolver_contract, fqdn: str, owner: str) -> bytes:
    node = namehash(fqdn)
    ctype = coin_type_for_chain(CHAIN_ID)
    try:
        data = resolver_contract.encodeABI(fn_name="setAddr", args=[node, ctype, HexBytes(to_checksum_address(owner))])
    except AttributeError:
        data = resolver_contract.functions.setAddr(node, ctype, HexBytes(to_checksum_address(owner)))._encode_transaction_data()
    return HexBytes(data)

def fetch_brokex_proof(pair_idx: int, proxy: Optional[str], retries=5, delay_sec=5) -> str:
    url = f"{BROKEX_PROOF_API}{pair_idx}"
    last = None
    proxies = {"http": proxy, "https": proxy} if proxy else None
    for i in range(1, retries+1):
        try:
            r = requests.get(url, headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}, timeout=15, proxies=proxies)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
            j = r.json()
            p = j.get("proof") or j.get("data") or j.get("result")
            if not p:
                raise RuntimeError("no 'proof' field")
            return p
        except Exception as e:
            last = e
            console.print(f"[warn]Proof retry {i}/{retries}: {e}[/warn]")
            time.sleep(delay_sec)
    raise RuntimeError(f"fetch_proof gagal: {last}")

def parse_wallets() -> List[Dict[str,str]]:
    out = []
    if Path(WALLETS_JSON).exists():
        try:
            data = json.loads(Path(WALLETS_JSON).read_text())
            for it in data:
                pk = str((it.get("private_key") if isinstance(it, dict) else it) or "").strip()
                if pk:
                    addr = Account.from_key("0x"+pk[2:] if pk.startswith("0x") else pk).address
                    out.append({"private_key": pk, "address": addr})
        except Exception:
            pass
    if not out and Path(WALLETS_TXT).exists():
        for raw in Path(WALLETS_TXT).read_text().splitlines():
            line=raw.strip()
            if not line or line.startswith("#"): continue
            pk=line.split(",")[0].strip()
            if pk:
                addr = Account.from_key("0x"+pk[2:] if pk.startswith("0x") else pk).address
                out.append({"private_key": pk, "address": addr})
    if not out and PRIVATE_KEY_ENV:
        addr = Account.from_key("0x"+PRIVATE_KEY_ENV[2:] if PRIVATE_KEY_ENV.startswith("0x") else PRIVATE_KEY_ENV).address
        out.append({"private_key": PRIVATE_KEY_ENV, "address": addr})
    return out

def _norm_proxy_url(p: str) -> Optional[str]:
    if not p: return None
    s=p.strip()
    if s.lower().startswith(("default=","all=")):
        s=s.split("=",1)[1].strip()
    if not re.match(r"^(http|https|socks5h?|SOCKS5H?)://", s): return None
    return s

def parse_proxies_simple(wallets: List[Dict[str,str]]) -> List[Optional[str]]:
    n=len(wallets)
    res=[None]*n
    if not Path(PROXIES_TXT).exists():
        return res
    default_proxy=None
    seq=[]
    by_addr={}
    lines=[L.strip() for L in Path(PROXIES_TXT).read_text().splitlines()]
    for line in lines:
        if not line or line.startswith("#"): continue
        if line.lower().startswith(("default=","all=")):
            p=_norm_proxy_url(line)
            if p: default_proxy=p
            continue
        if "," in line:
            addr, px = line.split(",",1)
            addr=addr.strip()
            px=_norm_proxy_url(px.strip())
            if px and re.match(r"^0x[0-9a-fA-F]{40}$", addr):
                by_addr[addr.lower()]=px
            continue
        p=_norm_proxy_url(line)
        if p: seq.append(p)
    for i,w in enumerate(wallets):
        a=w["address"].lower()
        if a in by_addr:
            res[i]=by_addr[a]
        elif i < len(seq):
            res[i]=seq[i]
        elif default_proxy:
            res[i]=default_proxy
        else:
            res[i]=None
    return res

def normalize_pk(pk: str) -> str:
    s = pk.strip()
    if s.startswith(("0x","0X")): s=s[2:]
    if not re.fullmatch(r"[0-9a-fA-F]{1,64}", s or ""): raise ValueError("PRIVATE_KEY invalid")
    s=s.rjust(64,"0").lower()
    if s=="0"*64: raise ValueError("PRIVATE_KEY zero")
    return "0x"+s

def make_provider(rpc_url: str, proxy: Optional[str]) -> Web3:
    kwargs={"timeout":60}
    if proxy: kwargs["proxies"]={"http":proxy,"https":proxy}
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs=kwargs))
    try:
        from web3.middleware.proof_of_authority import ExtraDataToPOAMiddleware
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except Exception:
        try:
            from web3.middleware import geth_poa_middleware
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        except Exception:
            pass
    if not w3.is_connected(): raise RuntimeError(f"Gagal konek RPC: {rpc_url}")
    return w3

def load_config() -> Dict[str,Any]:
    default = {
        "global":{"aio_sleep_hours":24},
        "programs":{
            "p1":{"enable_faucet":True,"amount_mode":"range","fixed":"0.05","min":"0.01","max":"0.09","repeat":5,"delay":120},
            "p2":{"count":5,"delay":180},
            "p3":{"swap_times":5,"swap_amount":"0.1","start_dir":"random","do_stake":True,"stake_mode":"random","stake_times":1,"stake_rand_min":1,"stake_rand_max":5,"stake_amount":"0.1","delay":60},
            "p4":{"runs":5,"delay":60},
            "p5":{"runs":5,"delay":180},
            "p6":{"runs":5,"delay":60,"amount":"0.1"}
        }
    }
    if Path(CONFIG_PATH).exists():
        try:
            cur=json.loads(Path(CONFIG_PATH).read_text())
            return {**default, **cur, "programs":{**default["programs"], **cur.get("programs",{})}}
        except Exception:
            return default
    Path(CONFIG_PATH).write_text(json.dumps(default, indent=2))
    return default

def save_config(cfg: Dict[str,Any]) -> None:
    Path(CONFIG_PATH).write_text(json.dumps(cfg, indent=2))

def ask_int(prompt: str, default: Optional[int]=None, minv: Optional[int]=None, maxv: Optional[int]=None) -> int:
    while True:
        s = console.input(f"[accent]?[/accent] {prompt}{f' [{default}]' if default is not None else ''}: ").strip()
        if not s and default is not None: v = default
        else:
            try: v = int(s)
            except: console.print("[warn]Masukkan bilangan bulat.[/warn]"); continue
        if minv is not None and v < minv: console.print(f"[warn]Min {minv}[/warn]"); continue
        if maxv is not None and v > maxv: console.print(f"[warn]Max {maxv}[/warn]"); continue
        return v

def ask_dec(prompt: str, default: Optional[Decimal]=None, minv: Optional[Decimal]=None, maxv: Optional[Decimal]=None) -> Decimal:
    while True:
        s = console.input(f"[accent]?[/accent] {prompt}{f' [{default}]' if default is not None else ''}: ").strip()
        if not s and default is not None: v = Decimal(default)
        else:
            try: v = Decimal(s)
            except: console.print("[warn]Masukkan angka desimal.[/warn]"); continue
        if minv is not None and v < minv: console.print(f"[warn]Min {minv}[/warn]"); continue
        if maxv is not None and v > maxv: console.print(f"[warn]Max {maxv}[/warn]"); continue
        return v

def p1_assets() -> List[Tuple[str,str]]:
    out=[]
    if re.match(r"^0x[0-9a-fA-F]{40}$", ASSET_GOLD): out.append(("GOLD",ASSET_GOLD))
    if re.match(r"^0x[0-9a-fA-F]{40}$", ASSET_TSLA): out.append(("TSLA",ASSET_TSLA))
    if re.match(r"^0x[0-9a-fA-F]{40}$", ASSET_NVIDIA): out.append(("NVIDIA",ASSET_NVIDIA))
    if re.match(r"^0x[0-9a-fA-F]{40}$", ASSET_USDC): out.append(("USDC",ASSET_USDC))
    if re.match(r"^0x[0-9a-fA-F]{40}$", ASSET_USDT): out.append(("USDT",ASSET_USDT))
    if re.match(r"^0x[0-9a-fA-F]{40}$", ASSET_WPHRS): out.append(("WPHRS",ASSET_WPHRS))
    return out

def p1_faucet_mint(w3: Web3, asset: str, to: str, human_amount_18: Decimal, label: str, pk: str):
    console.print(f"[muted]Faucet {label}[/muted]")
    try:
        f = w3.eth.contract(address=to_checksum_address(FAUCET_ADDRESS), abi=FAUCET_ABI)
        amt = to_units(human_amount_18, 18)
        tx = f.functions.mint(to_checksum_address(asset), to_checksum_address(to), int(amt)).build_transaction({**build_tx_common(w3, to), "gas": 120_000})
        ok, hx = sign_send_wait(w3, tx, pk, f"faucet {label}", 120_000)
        if ok: console.print(f"[ok]Faucet {label} {human_amount_18} • {tx_link(hx)}[/ok]")
        else: console.print(f"[err]Faucet {label} gagal[/err]")
    except Exception as e:
        console.print(f"[err]Faucet {label} gagal dikirim: {e}[/err]")

def p1_pool_supply(w3: Web3, token: str, sender: str, human_amount: Decimal, pk: str):
    ctoken = w3.eth.contract(address=to_checksum_address(token), abi=ERC20_ABI)
    pool  = w3.eth.contract(address=to_checksum_address(POOL_ADDRESS), abi=POOL_ABI)
    dec   = int(ctoken.functions.decimals().call())
    sym   = str(ctoken.functions.symbol().call())
    amt   = to_units(human_amount, dec)
    ensure_approval(w3, token, sender, POOL_ADDRESS, amt, pk)
    tx = pool.functions.supply(to_checksum_address(token), int(amt), to_checksum_address(sender), 0).build_transaction({**build_tx_common(w3, sender), "gas": 220_000})
    ok, hx = sign_send_wait(w3, tx, pk, f"supply {sym}", 220_000)
    if ok: console.print(f"[ok]Supply {sym} {human_amount} • {tx_link(hx)}[/ok]")
    else: console.print("[err]Supply gagal[/err]")

def run_program_1(pk: str, proxy: Optional[str], cfg: Dict[str,Any]):
    console.print(Rule(style="accent")); console.print("[title]Program 1 — Lend & Borrow[/title]", justify="center"); console.print(Rule(style="accent"))
    w3 = make_provider(RPC_URL, proxy); acct = Account.from_key(pk).address
    if cfg.get("enable_faucet", True):
        for label, addr in [("GOLD",ASSET_GOLD),("TSLA",ASSET_TSLA),("NVIDIA",ASSET_NVIDIA)]:
            if re.match(r"^0x[0-9a-fA-F]{40}$", addr):
                p1_faucet_mint(w3, addr, acct, FAUCET_AMOUNT, label, pk)
    assets = p1_assets()
    if not assets:
        console.print("[warn]Tidak ada aset untuk supply.[/warn]")
        return
    repeat = int(cfg.get("repeat",5)); delay = int(cfg.get("delay",120))
    mode = cfg.get("amount_mode","range")
    fixed = Decimal(str(cfg.get("fixed","0.05")))
    minv  = Decimal(str(cfg.get("min","0.01")))
    maxv  = Decimal(str(cfg.get("max","0.09")))
    for r in range(1, repeat+1):
        aset_now = assets[:]; random.shuffle(aset_now)
        console.print(Panel.fit(f"Siklus {r}/{repeat} — {len(aset_now)} tx", style="accent"))
        for i, (_, token) in enumerate(aset_now, 1):
            if mode == "fixed":
                amt = fixed
            else:
                amt = Decimal(str(random.uniform(float(minv), float(maxv)))).quantize(Decimal("0.000000000000000001"))
            try:
                p1_pool_supply(w3, token, acct, amt, pk)
            except Exception as e:
                console.print(f"[err]Supply gagal: {e}[/err]")
            if i < len(aset_now):
                sleep_countdown(int(delay + random.uniform(0, TX_DELAY_JITTER_SECS)), "Jeda")
        if r < repeat:
            sleep_countdown(int(delay + random.uniform(0, TX_DELAY_JITTER_SECS)), "Jeda antar siklus")

def random_label(min_len=12, max_len=22) -> str:
    import string
    n = random.randint(min_len, max_len)
    return "".join(random.choice(string.ascii_lowercase) for _ in range(n))

def p2_register_once(w3: Web3, controller, resolver, sender: str, pk: str) -> bool:
    duration = 365*24*3600
    label = random_label()
    fqdn = f"{label}.{TLD}"
    data_array = [encode_setaddr_calldata(resolver, fqdn, sender)]
    reverse = True
    price = controller.functions.rentPrice(label, duration).call()
    total = int(price[0]) + int(price[1])
    tip = (total * max(TIP_BPS, 0)) // 10000
    value_to_send = total + tip
    secret = HexBytes(os.urandom(32))
    commitment = controller.functions.makeCommitment(label, sender, duration, secret, to_checksum_address(RESOLVER), data_array, reverse, 0).call()
    tx = controller.functions.commit(commitment).build_transaction({**build_tx_common(w3, sender)})
    ok, _ = sign_send_wait(w3, tx, pk, "commit", 120_000)
    if not ok:
        return False
    try:
        min_age = int(controller.functions.minCommitmentAge().call())
    except Exception:
        min_age = 60
    sleep_countdown(min_age + EXTRA_WAIT, "Menunggu minCommitmentAge")
    tx = controller.functions.register(label, sender, duration, secret, to_checksum_address(RESOLVER), data_array, reverse, 0).build_transaction({**build_tx_common(w3, sender), "value": int(value_to_send), "gas": 500_000})
    ok, hx = sign_send_wait(w3, tx, pk, f"register {fqdn}", 500_000)
    if ok:
        console.print(f"[ok]Nama terdaftar: {fqdn} • {tx_link(hx)}[/ok]")
    return ok

def run_program_2(pk: str, proxy: Optional[str], cfg: Dict[str,Any]):
    console.print(Rule(style="accent")); console.print("[title]Program 2 — Add Domain[/title]", justify="center"); console.print(Rule(style="accent"))
    w3 = make_provider(RPC_URL, proxy); acct = Account.from_key(pk).address
    controller = w3.eth.contract(address=to_checksum_address(CONTROLLER), abi=CONTROLLER_ABI)
    resolver   = w3.eth.contract(address=to_checksum_address(RESOLVER),   abi=RESOLVER_ABI)
    count = int(cfg.get("count",5)); delay = int(cfg.get("delay",180))
    for i in range(1, count+1):
        console.print(Panel.fit(f"Registrasi {i}/{count}", style="accent"))
        try:
            ok = p2_register_once(w3, controller, resolver, acct, pk)
            if not ok: console.print("[err]Registrasi gagal[/err]")
        except Exception as e:
            console.print(f"[err]Gagal daftar: {e}[/err]")
        if i < count:
            sleep_countdown(delay, "Jeda sebelum domain berikutnya")
    console.print("[ok]Program 2 selesai.[/ok]")

def ensure_approval_tok(w3: Web3, acct: str, token: str, spender: str, min_amt: int, pk: str):
    c = w3.eth.contract(address=to_checksum_address(token), abi=ERC20_ABI)
    cur = int(c.functions.allowance(acct, to_checksum_address(spender)).call())
    if cur >= min_amt:
        return
    tx = c.functions.approve(to_checksum_address(spender), MAX_UINT256).build_transaction({**build_tx_common(w3, acct), "gas": 300_000})
    ok, _ = sign_send_wait(w3, tx, pk, "approve", 300_000)
    if not ok:
        raise RuntimeError("Approve gagal")

def swap_usdc_to_r2usd(w3: Web3, acct: str, amt: Decimal, dec_usdc: int, pk: str):
    units = to_units(amt, dec_usdc)
    ensure_approval_tok(w3, acct, R2USDC_ADDRESS, ROUTER_ADDRESS, units, pk)
    data = Web3.to_hex(SEL_USDC_TO_R2USD + abi_encode(["address","uint256","uint256","uint256","uint256","uint256","uint256"], [acct, units,0,0,0,0,0]))
    tx = {"to": to_checksum_address(ROUTER_ADDRESS), **build_tx_common(w3, acct), "data": data, "gas": 500_000, "value": 0}
    ok, _ = sign_send_wait(w3, tx, pk, "swap USDC→R2USD", 500_000)
    if not ok: raise RuntimeError("Swap reverted")

def swap_r2usd_to_usdc(w3: Web3, acct: str, amt: Decimal, dec_r2: int, pk: str):
    units = to_units(amt, dec_r2)
    ensure_approval_tok(w3, acct, R2USD_ADDRESS, ROUTER_ADDRESS, units, pk)
    data = Web3.to_hex(SEL_R2USD_TO_USDC + abi_encode(["address","uint256"], [acct, units]))
    tx = {"to": to_checksum_address(ROUTER_ADDRESS), **build_tx_common(w3, acct), "data": data, "gas": 500_000, "value": 0}
    ok, _ = sign_send_wait(w3, tx, pk, "swap R2USD→USDC", 500_000)
    if not ok: raise RuntimeError("Swap reverted")

def stake_r2usd(w3: Web3, acct: str, amt: Decimal, dec_r2: int, pk: str):
    units = to_units(amt, dec_r2)
    ensure_approval_tok(w3, acct, R2USD_ADDRESS, STAKING_CONTRACT, units, pk)
    data = Web3.to_hex(SEL_STAKE + abi_encode(["uint256","uint256","uint256","uint8","uint256","uint256"], [units,0,0,0,0,0]))
    tx = {"to": to_checksum_address(STAKING_CONTRACT), **build_tx_common(w3, acct), "data": data, "gas": 500_000, "value": 0}
    ok, _ = sign_send_wait(w3, tx, pk, "stake R2USD", 500_000)
    if not ok: raise RuntimeError("Stake reverted")

def run_program_3(pk: str, proxy: Optional[str], cfg: Dict[str,Any]):
    console.print(Rule(style="accent")); console.print("[title]Program 3 — Swap & Earn R2[/title]", justify="center"); console.print(Rule(style="accent"))
    w3 = make_provider(RPC_URL, proxy); acct = Account.from_key(pk).address
    du = get_decimals(w3, R2USDC_ADDRESS); dr = get_decimals(w3, R2USD_ADDRESS)
    d = cfg.get("start_dir","random"); d = 1 if d=="1" else (2 if d=="2" else random.choice([1,2]))
    swap_times = int(cfg.get("swap_times",5)); delay = int(cfg.get("delay",60))
    swap_amount = Decimal(str(cfg.get("swap_amount","0.1"))).quantize(Decimal("0.000001"))
    for i in range(1, swap_times+1):
        console.print(Panel.fit(f"SWAP {i}/{swap_times}", style="accent"))
        try:
            if d == 1: swap_usdc_to_r2usd(w3, acct, swap_amount, du, pk); d = 2
            else: swap_r2usd_to_usdc(w3, acct, swap_amount, dr, pk); d = 1
        except Exception as e:
            console.print(f"[err]Swap gagal: {e}[/err]")
        if i < swap_times: sleep_countdown(delay, "Jeda swap")
    if bool(cfg.get("do_stake",True)):
        sleep_countdown(delay, "Jeda sebelum STAKING")
        if cfg.get("stake_mode","random")=="random":
            times=random.randint(int(cfg.get("stake_rand_min",1)), int(cfg.get("stake_rand_max",5)))
        else:
            times=int(cfg.get("stake_times",1))
        stake_amount=Decimal(str(cfg.get("stake_amount","0.1"))).quantize(Decimal("0.000001"))
        for j in range(1, times+1):
            console.print(Panel.fit(f"STAKING {j}/{times}", style="accent"))
            try: stake_r2usd(w3, acct, stake_amount, dr, pk)
            except Exception as e: console.print(f"[err]Stake gagal: {e}[/err]")
            if j < times: sleep_countdown(delay, "Jeda staking")
    console.print("[ok]Program 3 selesai.[/ok]")

def ensure_approval_p4(w3: Web3, acct: str, token: str, spender: str, need: int, pk: str):
    c = w3.eth.contract(address=to_checksum_address(token), abi=ERC20_ABI)
    cur = int(c.functions.allowance(acct, to_checksum_address(spender)).call())
    if cur >= need: return
    tx = c.functions.approve(to_checksum_address(spender), MAX_UINT256).build_transaction({**build_tx_common(w3, acct), "gas":300_000})
    ok, _ = sign_send_wait(w3, tx, pk, "approve (Brokex)", 300_000)
    if not ok: raise RuntimeError("Approve gagal")

def brokex_trade_once(w3: Web3, acct: str, pk: str, proxy: Optional[str]):
    dec = get_decimals(w3, BROKEX_USDT_ADDRESS)
    amount = Decimal(random.uniform(15,20)).quantize(Decimal("0.000001"))
    units  = to_units(amount, dec)
    ensure_approval_p4(w3, acct, BROKEX_USDT_ADDRESS, BROKEX_POOL_ROUTER_ADDRESS, units, pk)
    ensure_approval_p4(w3, acct, BROKEX_USDT_ADDRESS, BROKEX_TRADE_ROUTER_ADDRESS, units, pk)
    pair = random.choice(BROKEX_PAIRS); is_long = random.choice([True, False])
    proof = fetch_brokex_proof(pair["idx"], proxy)
    c = w3.eth.contract(address=to_checksum_address(BROKEX_TRADE_ROUTER_ADDRESS), abi=BROKEX_ABI)
    tx = c.functions.openPosition(int(pair["idx"]), proof, bool(is_long), 1, int(units), 0, 0).build_transaction({**build_tx_common(w3, acct), "gas": 2_000_000})
    ok, hx = sign_send_wait(w3, tx, pk, f"Brokex {pair['name']} {'Long' if is_long else 'Short'} size {amount}", 2_000_000)
    if not ok: raise RuntimeError("openPosition reverted")
    console.print(f"[ok]Trade • {tx_link(hx)}[/ok]")

def run_program_4(pk: str, proxy: Optional[str], cfg: Dict[str,Any]):
    console.print(Rule(style="accent")); console.print("[title]Program 4 — Brokex Trade[/title]", justify="center"); console.print(Rule(style="accent"))
    w3 = make_provider(RPC_URL, proxy); acct = Account.from_key(pk).address
    runs=int(cfg.get("runs",5)); delay=int(cfg.get("delay",60))
    for i in range(1, runs+1):
        console.print(Panel.fit(f"Trade {i}/{runs}", style="accent"))
        try: brokex_trade_once(w3, acct, pk, proxy)
        except Exception as e: console.print(f"[err]Trade gagal: {e}[/err]")
        if i < runs: sleep_countdown(delay, "Jeda trade")
    console.print("[ok]Program 4 selesai.[/ok]")

def ensure_approve_p5(w3: Web3, sender: str, token: str, spender: str, need: int, pk: str) -> bool:
    c = w3.eth.contract(address=to_checksum_address(token), abi=ERC20_ABI)
    cur = int(c.functions.allowance(sender, to_checksum_address(spender)).call())
    if cur >= need: return True
    try:
        amt = MAX_UINT256 if MAX_APPROVE_P5 else need
        tx = c.functions.approve(to_checksum_address(spender), int(amt)).build_transaction({**build_tx_common(w3, sender), "gas": int(70000*GAS_MULT_P5)})
        ok, _ = sign_send_wait(w3, tx, pk, "approve (P5)", int(70000*GAS_MULT_P5))
        return ok
    except Exception as e:
        console.print(f"[err]Approve gagal: {e}[/err]"); return False

def do_deposit_once(w3: Web3, sender: str, token: str, depo_addr: str, human_amount: Decimal, pk: str) -> bool:
    ctoken = w3.eth.contract(address=to_checksum_address(token), abi=ERC20_ABI)
    dep    = w3.eth.contract(address=to_checksum_address(depo_addr), abi=DEPOSIT_ABI)
    dec    = int(ctoken.functions.decimals().call())
    units  = to_units(human_amount, dec)
    if not ensure_approve_p5(w3, sender, token, depo_addr, units, pk): return False
    tx = dep.functions.deposit(to_checksum_address(token), int(units)).build_transaction({**build_tx_common(w3, sender), "gas": int(120000*GAS_MULT_P5)})
    ok, hx = sign_send_wait(w3, tx, pk, f"deposit {human_amount}", int(120000*GAS_MULT_P5))
    if ok: console.print(f"[ok]Deposit • {tx_link(hx)}[/ok]")
    return ok

def run_program_5(pk: str, proxy: Optional[str], cfg: Dict[str,Any]):
    console.print(Rule(style="accent")); console.print("[title]Program 5 — RwaTrade (Deposit)[/title]", justify="center"); console.print(Rule(style="accent"))
    w3 = make_provider(RPC_URL, proxy); sender = Account.from_key(pk).address
    runs = int(cfg.get("runs",5)); delay=int(cfg.get("delay",180))
    for i in range(1, runs+1):
        console.print(Panel.fit(f"Deposit {i}/{runs} • amount {DEPOSIT_AMOUNT_P5}", style="accent"))
        try: do_deposit_once(w3, sender, TOKEN_ADDRESS_P5, DEPOSIT_CONTRACT_P5, DEPOSIT_AMOUNT_P5, pk)
        except Exception as e: console.print(f"[err]Deposit gagal: {e}[/err]")
        if i < runs: sleep_countdown(delay, "Jeda deposit")
    console.print("[ok]Program 5 selesai.[/ok]")

def ensure_allow_spout(w3: Web3, acct: str, dec: int, need_amt: Decimal, pk: str):
    c = w3.eth.contract(address=to_checksum_address(USDC_SP_ADDRESS), abi=ERC20_ABI)
    allow = int(c.functions.allowance(acct, to_checksum_address(SPOUT_SPENDER)).call())
    need  = to_units(need_amt, dec)
    if allow >= need: return
    want  = to_units(APPROVE_AMOUNT_USDC, dec)
    tx = c.functions.approve(to_checksum_address(SPOUT_SPENDER), int(want)).build_transaction({**build_tx_common(w3, acct), "gas": 100_000})
    ok, _ = sign_send_wait(w3, tx, pk, "approve (Spout)", 100_000)
    if not ok: raise RuntimeError("Approve gagal")

def spout_transfer_once(w3: Web3, acct: str, dec: int, amt: Decimal, pk: str):
    c = w3.eth.contract(address=to_checksum_address(USDC_SP_ADDRESS), abi=ERC20_ABI)
    units = to_units(amt, dec)
    ensure_allow_spout(w3, acct, dec, amt, pk)
    tx = c.functions.transfer(to_checksum_address(SPOUT_SPENDER), int(units)).build_transaction({**build_tx_common(w3, acct), "gas": 150_000})
    ok, hx = sign_send_wait(w3, tx, pk, f"transfer {amt} USDC", 150_000)
    if not ok: raise RuntimeError("Transfer gagal")
    console.print(f"[ok]Transfer • {tx_link(hx)}[/ok]")

def run_program_6(pk: str, proxy: Optional[str], cfg: Dict[str,Any]):
    console.print(Rule(style="accent")); console.print("[title]Program 6 — Spout (USDC Transfer)[/title]", justify="center"); console.print(Rule(style="accent"))
    w3 = make_provider(RPC_URL, proxy); acct = Account.from_key(pk).address
    dec = get_decimals(w3, USDC_SP_ADDRESS)
    runs=int(cfg.get("runs",5)); delay=int(cfg.get("delay",60)); amount=Decimal(str(cfg.get("amount","0.1")))
    for i in range(1, runs+1):
        console.print(Panel.fit(f"Transfer {i}/{runs} • {amount} USDC", style="accent"))
        try: spout_transfer_once(w3, acct, dec, amount, pk)
        except Exception as e: console.print(f"[err]Transfer gagal: {e}[/err]")
        if i < runs: sleep_countdown(delay, "Jeda transfer")
    console.print("[ok]Program 6 selesai.[/ok]")

def set_default_config(cfg: Dict[str,Any]) -> Dict[str,Any]:
    while True:
        console.print(Rule(style="accent")); console.print("[title]Set Default Config[/title]", justify="center"); console.print(Rule(style="accent"))
        console.print("[accent]1[/accent]) Global")
        console.print("[accent]2[/accent]) P1 — Lend & Borrow")
        console.print("[accent]3[/accent]) P2 — Add Domain")
        console.print("[accent]4[/accent]) P3 — Swap & Earn R2")
        console.print("[accent]5[/accent]) P4 — Brokex Trade")
        console.print("[accent]6[/accent]) P5 — RwaTrade")
        console.print("[accent]7[/accent]) P6 — Spout")
        console.print("[accent]8[/accent]) Kembali")
        ch = console.input("[accent]Pilih[/accent]: ").strip()
        if ch == "1":
            cur=cfg["global"]; h=ask_int("All-in-one repeat (jam)", cur.get("aio_sleep_hours",24), 1, 240)
            cfg["global"]["aio_sleep_hours"]=h; save_config(cfg); console.print("[ok]Global tersimpan.[/ok]")
        elif ch == "2":
            cur=cfg["programs"]["p1"]
            yn=console.input(f"[accent]?[/accent] Aktifkan faucet? (y/n) [{'y' if cur.get('enable_faucet',True) else 'n'}]: ").strip().lower() or ('y' if cur.get('enable_faucet',True) else 'n')
            cfg["programs"]["p1"]["enable_faucet"]= yn in ("y","yes","ya")
            md=console.input(f"[accent]?[/accent] Amount mode (fixed/range) [{cur.get('amount_mode','range')}]: ").strip() or cur.get("amount_mode","range")
            if md not in ("fixed","range"): md="range"
            cfg["programs"]["p1"]["amount_mode"]=md
            if md=="fixed":
                cfg["programs"]["p1"]["fixed"]=str(ask_dec("Fixed amount", Decimal(str(cur.get("fixed","0.05"))), Decimal("0.000000000000000001")))
            else:
                mn=ask_dec("Min amount", Decimal(str(cur.get("min","0.01"))), Decimal("0.000000000000000001"))
                mx=ask_dec("Max amount", Decimal(str(cur.get("max","0.09"))), mn)
                cfg["programs"]["p1"]["min"]=str(mn); cfg["programs"]["p1"]["max"]=str(mx)
            cfg["programs"]["p1"]["repeat"]=ask_int("Repeat cycles", int(cur.get("repeat",5)), 1, 1000)
            cfg["programs"]["p1"]["delay"]=ask_int("Delay (s)", int(cur.get("delay",120)), 0, 3600)
            save_config(cfg); console.print("[ok]P1 tersimpan.[/ok]")
        elif ch == "3":
            cur=cfg["programs"]["p2"]
            cfg["programs"]["p2"]["count"]=ask_int("Jumlah domain per siklus", int(cur.get("count",5)), 1, 100000)
            cfg["programs"]["p2"]["delay"]=ask_int("Jeda antar pendaftaran (s)", int(cur.get("delay",180)), 0, 3600)
            save_config(cfg); console.print("[ok]P2 tersimpan.[/ok]")
        elif ch == "4":
            cur=cfg["programs"]["p3"]
            cfg["programs"]["p3"]["swap_times"]=ask_int("Swap times", int(cur.get("swap_times",5)), 1, 5000)
            cfg["programs"]["p3"]["swap_amount"]=str(ask_dec("Swap amount", Decimal(str(cur.get("swap_amount","0.1"))), Decimal("0.000001")))
            st=console.input(f"[accent]?[/accent] Start dir (1/2/random) [{cur.get('start_dir','random')}]: ").strip() or cur.get("start_dir","random")
            cfg["programs"]["p3"]["start_dir"]= st if st in ("1","2","random") else "random"
            yn=console.input(f"[accent]?[/accent] Do stake? (y/n) [{'y' if cur.get('do_stake',True) else 'n'}]: ").strip().lower() or ('y' if cur.get('do_stake',True) else 'n')
            cfg["programs"]["p3"]["do_stake"]= yn in ("y","yes","ya")
            if cfg["programs"]["p3"]["do_stake"]:
                sm=console.input(f"[accent]?[/accent] Stake mode (random/fixed) [{cur.get('stake_mode','random')}]: ").strip() or cur.get("stake_mode","random")
                sm= sm if sm in ("random","fixed") else "random"
                cfg["programs"]["p3"]["stake_mode"]=sm
                if sm=="fixed":
                    cfg["programs"]["p3"]["stake_times"]=ask_int("Stake times", int(cur.get("stake_times",1)), 1, 10000)
                else:
                    cfg["programs"]["p3"]["stake_rand_min"]=ask_int("Stake rand MIN", int(cur.get("stake_rand_min",1)), 1, 10000)
                    cfg["programs"]["p3"]["stake_rand_max"]=ask_int("Stake rand MAX", int(cur.get("stake_rand_max",5)), int(cfg["programs"]["p3"]["stake_rand_min"]), 10000)
                cfg["programs"]["p3"]["stake_amount"]=str(ask_dec("Stake amount", Decimal(str(cur.get("stake_amount","0.1"))), Decimal("0.000001")))
            cfg["programs"]["p3"]["delay"]=ask_int("Delay (s)", int(cur.get("delay",60)), 0, 3600)
            save_config(cfg); console.print("[ok]P3 tersimpan.[/ok]")
        elif ch == "5":
            cur=cfg["programs"]["p4"]
            cfg["programs"]["p4"]["runs"]=ask_int("Jumlah trade per siklus", int(cur.get("runs",5)), 1, 100000)
            cfg["programs"]["p4"]["delay"]=ask_int("Jeda antar trade (s)", int(cur.get("delay",60)), 0, 3600)
            save_config(cfg); console.print("[ok]P4 tersimpan.[/ok]")
        elif ch == "6":
            cur=cfg["programs"]["p5"]
            cfg["programs"]["p5"]["runs"]=ask_int("Jumlah deposit per siklus", int(cur.get("runs",5)), 1, 100000)
            cfg["programs"]["p5"]["delay"]=ask_int("Jeda antar deposit (s)", int(cur.get("delay",180)), 0, 3600)
            save_config(cfg); console.print("[ok]P5 tersimpan.[/ok]")
        elif ch == "7":
            cur=cfg["programs"]["p6"]
            cfg["programs"]["p6"]["runs"]=ask_int("Jumlah transfer per siklus", int(cur.get("runs",5)), 1, 100000)
            cfg["programs"]["p6"]["delay"]=ask_int("Jeda antar transfer (s)", int(cur.get("delay",60)), 0, 3600)
            cfg["programs"]["p6"]["amount"]=str(ask_dec("Amount per transfer (USDC)", Decimal(str(cur.get("amount","0.1"))), Decimal("0.000001")))
            save_config(cfg); console.print("[ok]P6 tersimpan.[/ok]")
        elif ch == "8":
            break
        else:
            console.print("[warn]Pilihan tak dikenal.[/warn]")
    return cfg

def pick_account(wallets: List[Dict[str,str]]) -> Optional[int]:
    if not wallets: return None
    if len(wallets)==1: return 0
    console.print(Rule(style="accent")); console.print("[title]Pilih Akun[/title]", justify="center"); console.print(Rule(style="accent"))
    for i,w in enumerate(wallets, start=1):
        console.print(f"[accent]{i}[/accent]) {w['address']}")
    console.print(f"[accent]{len(wallets)+1}[/accent]) Semua akun (urut)")
    ch = ask_int("Pilih", 1, 1, len(wallets)+1)
    if ch==len(wallets)+1: return -1
    return ch-1

def run_individual(cfg: Dict[str,Any], wallets: List[Dict[str,str]], proxies: List[Optional[str]]):
    idx = pick_account(wallets)
    if idx is None:
        console.print("[err]Tidak ada akun. Set PRIVATE_KEY di .env atau wallets.json[/err]")
        return
    indices = list(range(len(wallets))) if idx==-1 else [idx]
    console.print(Rule(style="accent")); console.print("[title]Pilih Program[/title]", justify="center"); console.print(Rule(style="accent"))
    console.print("[accent]1[/accent]) P1 — Lend & Borrow")
    console.print("[accent]2[/accent]) P2 — Add Domain")
    console.print("[accent]3[/accent]) P3 — Swap & Earn R2")
    console.print("[accent]4[/accent]) P4 — Brokex Trade")
    console.print("[accent]5[/accent]) P5 — RwaTrade")
    console.print("[accent]6[/accent]) P6 — Spout")
    console.print("[accent]7[/accent]) Kembali")
    ch = ask_int("Pilih", 1, 1, 7)
    if ch==7: return
    for i in indices:
        pk=normalize_pk(wallets[i]["private_key"]); proxy=proxies[i]
        try:
            if ch==1: run_program_1(pk, proxy, cfg["programs"]["p1"])
            elif ch==2: run_program_2(pk, proxy, cfg["programs"]["p2"])
            elif ch==3: run_program_3(pk, proxy, cfg["programs"]["p3"])
            elif ch==4: run_program_4(pk, proxy, cfg["programs"]["p4"])
            elif ch==5: run_program_5(pk, proxy, cfg["programs"]["p5"])
            elif ch==6: run_program_6(pk, proxy, cfg["programs"]["p6"])
        except KeyboardInterrupt:
            console.print("\n[warn]Dihentikan oleh user.[/warn]"); break
        except Exception as e:
            console.print(f"[err]Error akun {i+1}: {e}[/err]")

def all_in_one(cfg: Dict[str,Any], wallets: List[Dict[str,str]], proxies: List[Optional[str]]):
    if not wallets:
        console.print("[err]Tidak ada akun. Set PRIVATE_KEY di .env atau wallets.json[/err]")
        return
    console.print(Rule(style="accent")); console.print("[title]All in One Run[/title]", justify="center"); console.print(Rule(style="accent"))
    console.print("[muted]Mode ini akan menjalankan P1→P6 lalu mengulang setiap 24 jam. Tekan Ctrl+C untuk berhenti.[/muted]")
    while True:
        try:
            for i,w in enumerate(wallets, start=1):
                pk=normalize_pk(w["private_key"]); proxy=proxies[i-1]
                console.print(Panel.fit(f"Akun {i}/{len(wallets)} • {w['address']}", border_style="accent"))
                try: run_program_1(pk, proxy, cfg["programs"]["p1"])
                except Exception as e: console.print(f"[err]P1 error: {e}[/err]")
                try: run_program_2(pk, proxy, cfg["programs"]["p2"])
                except Exception as e: console.print(f"[err]P2 error: {e}[/err]")
                try: run_program_3(pk, proxy, cfg["programs"]["p3"])
                except Exception as e: console.print(f"[err]P3 error: {e}[/err]")
                try: run_program_4(pk, proxy, cfg["programs"]["p4"])
                except Exception as e: console.print(f"[err]P4 error: {e}[/err]")
                try: run_program_5(pk, proxy, cfg["programs"]["p5"])
                except Exception as e: console.print(f"[err]P5 error: {e}[/err]")
                try: run_program_6(pk, proxy, cfg["programs"]["p6"])
                except Exception as e: console.print(f"[err]P6 error: {e}[/err]")
            hours = int(cfg["global"].get("aio_sleep_hours",24))
            console.print(Panel.fit(f"Selesai semua program untuk semua akun. Tidur {hours} jam…", border_style="accent"))
            sleep_countdown(hours*3600, f"Tidur {hours} jam")
        except KeyboardInterrupt:
            console.print("\n[warn]Dihentikan oleh user.[/warn]"); break
        except Exception as e:
            console.print(f"[err]Error siklus: {e}[/err]"); sleep_countdown(60, "Tunggu 60s & lanjut")

def main_menu():
    cfg = load_config()
    wallets = parse_wallets()
    proxies = parse_proxies_simple(wallets)
    while True:
        console.print(Rule(style="accent")); console.print("[title]Pharos — Unified Runner[/title]", justify="center"); console.print(Rule(style="accent"))
        t=Table(box=box.ROUNDED, show_header=True, header_style="accent"); t.add_column("No"); t.add_column("Menu", style="title")
        t.add_row("1","All in One Run (loop 24 jam)"); t.add_row("2","Set Default Config"); t.add_row("3","Individual Run"); t.add_row("4","Keluar"); console.print(t)
        ch = console.input("[accent]Pilih[/accent]: ").strip()
        if ch=="1": all_in_one(cfg, wallets, proxies)
        elif ch=="2": cfg=set_default_config(cfg); save_config(cfg)
        elif ch=="3": run_individual(cfg, wallets, proxies)
        elif ch=="4": console.print("[muted]Bye.[/muted]"); break
        else: console.print("[warn]Pilihan tak dikenal.[/warn]")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[warn]Dihentikan oleh user.[/warn]")
