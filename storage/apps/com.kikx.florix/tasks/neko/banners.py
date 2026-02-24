from .ui import Pre, Text, Animate

B1 = Animate(Pre(Text(r"""
♡  /)/)
 （„• ֊ •„)♡              
┏ • UU • - • - • - • - • - • - • ღ❦ღ┓
              <span class="text-blue-300 font-bold">FLORIX NEKO</span> 
            A <span class="text-red-300">Script</span> Runner 
┗ღ❦ღ • - • - • - • - • - • - • - •  ┛
     \(•.•)/              \(•.•)/
       | |                  | |
      _/ \_                _/ \_
/````````````````````````````````````\
""")))
B1.add_class("w-full h-full flex items-end justify-center")

B2 = Animate(Pre(Text(r"""
  /)/) E            K (\(\
 (•.•)/              \(•.•)
N/| |      FLORIX      | |\O
 _/ \_                _/ \_
""")), "slideInUp")
B2.add_class("w-full h-full flex items-end justify-center text-sm")

B3 = Animate(Pre(Text(r"""
(`“ •.  (`“•.¸🌼¸.•“´)  ¸. •“´)
    🌸«•🍃   NEKO  🍃•“»🌸
(¸. • “´(¸.•“´🌼 `“•)` “° •.¸)
""")), "rubberBand")
B3.add_class("w-full h-full flex items-center justify-center")

B4 = Animate(Pre(Text(r"""
   /)/)  FLORIX
  (•.•)丿  X   NEKO
ノ/   /  
ノ￣ゝ 
""")), "lightSpeedInLeft")
B4.add_class("w-full h-full flex justify-start items-end text-sm")

B5 = Animate(Pre(Text(r"""┊    ┊    ┊    ┊    ┊    ┊
┊    ┊    ┊    ┊    ┊    💗
┊    ┊    ┊    ┊    ❤️    X
┊    ┊    ┊   💛     I  
┊    ┊   💚    R  
┊   💙    O  
💜   L  
F 
""")), "fadeInDownBig")
B5.add_class("w-full h-full flex justify-center items-start text-sm")


BANNERS = [B1, B2, B3, B5]

