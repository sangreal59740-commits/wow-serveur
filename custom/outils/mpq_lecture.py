import struct,zlib,sys
def ct():
    t=[0]*0x500; s=0x00100001
    for i in range(0x100):
        j=i
        for _ in range(5):
            s=(s*125+3)%0x2AAAAB; a=(s&0xFFFF)<<16
            s=(s*125+3)%0x2AAAAB; t[j]=a|(s&0xFFFF); j+=0x100
    return t
T=ct()
def h(s,ty):
    s1,s2=0x7FED7FED,0xEEEEEEEE
    for c in s.upper().replace('/','\\'):
        v=ord(c); s1=(T[ty*0x100+v]^(s1+s2))&0xFFFFFFFF; s2=(v+s1+s2+(s2<<5)+3)&0xFFFFFFFF
    return s1
def dec(d,key):
    s2=0xEEEEEEEE; o=[]
    for (v,) in struct.iter_unpack('<I',d):
        s2=(s2+T[0x400+(key&0xFF)])&0xFFFFFFFF; r=v^((key+s2)&0xFFFFFFFF); o.append(r)
        key=((~key<<0x15)+0x11111111|(key>>0x0B))&0xFFFFFFFF; s2=(r+s2+(s2<<5)+3)&0xFFFFFFFF
    return struct.pack('<%dI'%len(o),*o)
