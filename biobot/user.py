import dataclasses
import typing

import platform
if platform == "CPython":
    import regex
    USERNAME_REGEX = regex.compile(r'(?<!\pL|\pN|_)@([a-z](?:_(?!_)|[a-z0-9]){2,30}[a-z0-9]|gif|pic|vid)(?!\pL|\pN|_)', regex.I | regex.V1)
else:
    import re
    # generated by pasting the above regex into generate_regex.py
    USERNAME_REGEX = re.compile('(?<![A-Za-zªµºÀ-ÖØ-öø-ˁˆ-ˑˠ-ˤˬˮͰ-ʹͶͷͺ-ͽͿΆΈ-ΊΌΎ-ΡΣ-ϵϷ-ҁҊ-ԯԱ-Ֆՙՠ-ֈא-תׯ-ײؠ-يٮٯٱ-ۓەۥۦۮۯۺ-ۼۿܐܒ-ܯݍ-ޥޱߊ-ߪߴߵߺࠀ-ࠕࠚࠤࠨࡀ-ࡘࡠ-ࡪ\u0870-\u0887\u0889-\u088eࢠ-\u08c9ऄ-हऽॐक़-ॡॱ-ঀঅ-ঌএঐও-নপ-রলশ-হঽৎড়ঢ়য়-ৡৰৱৼਅ-ਊਏਐਓ-ਨਪ-ਰਲਲ਼ਵਸ਼ਸਹਖ਼-ੜਫ਼ੲ-ੴઅ-ઍએ-ઑઓ-નપ-રલળવ-હઽૐૠૡૹଅ-ଌଏଐଓ-ନପ-ରଲଳଵ-ହଽଡ଼ଢ଼ୟ-ୡୱஃஅ-ஊஎ-ஐஒ-கஙசஜஞடணதந-பம-ஹௐఅ-ఌఎ-ఐఒ-నప-హఽౘ-ౚ\u0c5dౠౡಀಅ-ಌಎ-ಐಒ-ನಪ-ಳವ-ಹಽ\u0cddೞೠೡೱೲഄ-ഌഎ-ഐഒ-ഺഽൎൔ-ൖൟ-ൡൺ-ൿඅ-ඖක-නඳ-රලව-ෆก-ะาำเ-ๆກຂຄຆ-ຊຌ-ຣລວ-ະາຳຽເ-ໄໆໜ-ໟༀཀ-ཇཉ-ཬྈ-ྌက-ဪဿၐ-ၕၚ-ၝၡၥၦၮ-ၰၵ-ႁႎႠ-ჅჇჍა-ჺჼ-ቈቊ-ቍቐ-ቖቘቚ-ቝበ-ኈኊ-ኍነ-ኰኲ-ኵኸ-ኾዀዂ-ዅወ-ዖዘ-ጐጒ-ጕጘ-ፚᎀ-ᎏᎠ-Ᏽᏸ-ᏽᐁ-ᙬᙯ-ᙿᚁ-ᚚᚠ-ᛪᛱ-ᛸᜀ-ᜑ\u171f-ᜱᝀ-ᝑᝠ-ᝬᝮ-ᝰក-ឳៗៜᠠ-ᡸᢀ-ᢄᢇ-ᢨᢪᢰ-ᣵᤀ-ᤞᥐ-ᥭᥰ-ᥴᦀ-ᦫᦰ-ᧉᨀ-ᨖᨠ-ᩔᪧᬅ-ᬳᭅ-\u1b4cᮃ-ᮠᮮᮯᮺ-ᯥᰀ-ᰣᱍ-ᱏᱚ-ᱽᲀ-ᲈᲐ-ᲺᲽ-Ჿᳩ-ᳬᳮ-ᳳᳵᳶᳺᴀ-ᶿḀ-ἕἘ-Ἕἠ-ὅὈ-Ὅὐ-ὗὙὛὝὟ-ώᾀ-ᾴᾶ-ᾼιῂ-ῄῆ-ῌῐ-ΐῖ-Ίῠ-Ῥῲ-ῴῶ-ῼⁱⁿₐ-ₜℂℇℊ-ℓℕℙ-ℝℤΩℨK-ℭℯ-ℹℼ-ℿⅅ-ⅉⅎↃↄⰀ-ⳤⳫ-ⳮⳲⳳⴀ-ⴥⴧⴭⴰ-ⵧⵯⶀ-ⶖⶠ-ⶦⶨ-ⶮⶰ-ⶶⶸ-ⶾⷀ-ⷆⷈ-ⷎⷐ-ⷖⷘ-ⷞⸯ々〆〱-〵〻〼ぁ-ゖゝ-ゟァ-ヺー-ヿㄅ-ㄯㄱ-ㆎㆠ-ㆿㇰ-ㇿ㐀-䶿一-ꒌꓐ-ꓽꔀ-ꘌꘐ-ꘟꘪꘫꙀ-ꙮꙿ-ꚝꚠ-ꛥꜗ-ꜟꜢ-ꞈꞋ-ꟊ\ua7d0\ua7d1\ua7d3\ua7d5-\ua7d9\ua7f2-ꠁꠃ-ꠅꠇ-ꠊꠌ-ꠢꡀ-ꡳꢂ-ꢳꣲ-ꣷꣻꣽꣾꤊ-ꤥꤰ-ꥆꥠ-ꥼꦄ-ꦲꧏꧠ-ꧤꧦ-ꧯꧺ-ꧾꨀ-ꨨꩀ-ꩂꩄ-ꩋꩠ-ꩶꩺꩾ-ꪯꪱꪵꪶꪹ-ꪽꫀꫂꫛ-ꫝꫠ-ꫪꫲ-ꫴꬁ-ꬆꬉ-ꬎꬑ-ꬖꬠ-ꬦꬨ-ꬮꬰ-ꭚꭜ-ꭩꭰ-ꯢ가-힣ힰ-ퟆퟋ-ퟻ豈-舘並-龎ﬀ-ﬆﬓ-ﬗיִײַ-ﬨשׁ-זּטּ-לּמּנּסּףּפּצּ-ﮱﯓ-ﴽﵐ-ﶏﶒ-ﷇﷰ-ﷻﹰ-ﹴﹶ-ﻼＡ-Ｚａ-ｚｦ-ﾾￂ-ￇￊ-ￏￒ-ￗￚ-ￜ𐀀-𐀋𐀍-𐀦𐀨-𐀺𐀼𐀽𐀿-𐁍𐁐-𐁝𐂀-𐃺𐊀-𐊜𐊠-𐋐𐌀-𐌟𐌭-𐍀𐍂-𐍉𐍐-𐍵𐎀-𐎝𐎠-𐏃𐏈-𐏏𐐀-𐒝𐒰-𐓓𐓘-𐓻𐔀-𐔧𐔰-𐕣\U00010570-\U0001057a\U0001057c-\U0001058a\U0001058c-\U00010592\U00010594\U00010595\U00010597-\U000105a1\U000105a3-\U000105b1\U000105b3-\U000105b9\U000105bb\U000105bc𐘀-𐜶𐝀-𐝕𐝠-𐝧\U00010780-\U00010785\U00010787-\U000107b0\U000107b2-\U000107ba𐠀-𐠅𐠈𐠊-𐠵𐠷𐠸𐠼𐠿-𐡕𐡠-𐡶𐢀-𐢞𐣠-𐣲𐣴𐣵𐤀-𐤕𐤠-𐤹𐦀-𐦷𐦾𐦿𐨀𐨐-𐨓𐨕-𐨗𐨙-𐨵𐩠-𐩼𐪀-𐪜𐫀-𐫇𐫉-𐫤𐬀-𐬵𐭀-𐭕𐭠-𐭲𐮀-𐮑𐰀-𐱈𐲀-𐲲𐳀-𐳲𐴀-𐴣𐺀-𐺩𐺰𐺱𐼀-𐼜𐼧𐼰-𐽅\U00010f70-\U00010f81𐾰-𐿄𐿠-𐿶𑀃-𑀷\U00011071\U00011072\U00011075𑂃-𑂯𑃐-𑃨𑄃-𑄦𑅄𑅇𑅐-𑅲𑅶𑆃-𑆲𑇁-𑇄𑇚𑇜𑈀-𑈑𑈓-𑈫\U0001123f\U00011240𑊀-𑊆𑊈𑊊-𑊍𑊏-𑊝𑊟-𑊨𑊰-𑋞𑌅-𑌌𑌏𑌐𑌓-𑌨𑌪-𑌰𑌲𑌳𑌵-𑌹𑌽𑍐𑍝-𑍡𑐀-𑐴𑑇-𑑊𑑟-𑑡𑒀-𑒯𑓄𑓅𑓇𑖀-𑖮𑗘-𑗛𑘀-𑘯𑙄𑚀-𑚪𑚸𑜀-𑜚\U00011740-\U00011746𑠀-𑠫𑢠-𑣟𑣿-𑤆𑤉𑤌-𑤓𑤕𑤖𑤘-𑤯𑤿𑥁𑦠-𑦧𑦪-𑧐𑧡𑧣𑨀𑨋-𑨲𑨺𑩐𑩜-𑪉𑪝\U00011ab0-𑫸𑰀-𑰈𑰊-𑰮𑱀𑱲-𑲏𑴀-𑴆𑴈𑴉𑴋-𑴰𑵆𑵠-𑵥𑵧𑵨𑵪-𑶉𑶘𑻠-𑻲\U00011f02\U00011f04-\U00011f10\U00011f12-\U00011f33𑾰𒀀-𒎙𒒀-𒕃\U00012f90-\U00012ff0𓀀-\U0001342f\U00013441-\U00013446𔐀-𔙆𖠀-𖨸𖩀-𖩞\U00016a70-\U00016abe𖫐-𖫭𖬀-𖬯𖭀-𖭃𖭣-𖭷𖭽-𖮏𖹀-𖹿𖼀-𖽊𖽐𖾓-𖾟𖿠𖿡𖿣𗀀-𘟷𘠀-𘳕𘴀-𘴈\U0001aff0-\U0001aff3\U0001aff5-\U0001affb\U0001affd\U0001affe𛀀-\U0001b122\U0001b132𛅐-𛅒\U0001b155𛅤-𛅧𛅰-𛋻𛰀-𛱪𛱰-𛱼𛲀-𛲈𛲐-𛲙𝐀-𝑔𝑖-𝒜𝒞𝒟𝒢𝒥𝒦𝒩-𝒬𝒮-𝒹𝒻𝒽-𝓃𝓅-𝔅𝔇-𝔊𝔍-𝔔𝔖-𝔜𝔞-𝔹𝔻-𝔾𝕀-𝕄𝕆𝕊-𝕐𝕒-𝚥𝚨-𝛀𝛂-𝛚𝛜-𝛺𝛼-𝜔𝜖-𝜴𝜶-𝝎𝝐-𝝮𝝰-𝞈𝞊-𝞨𝞪-𝟂𝟄-𝟋\U0001df00-\U0001df1e\U0001df25-\U0001df2a\U0001e030-\U0001e06d𞄀-𞄬𞄷-𞄽𞅎\U0001e290-\U0001e2ad𞋀-𞋫\U0001e4d0-\U0001e4eb\U0001e7e0-\U0001e7e6\U0001e7e8-\U0001e7eb\U0001e7ed\U0001e7ee\U0001e7f0-\U0001e7fe𞠀-𞣄𞤀-𞥃𞥋𞸀-𞸃𞸅-𞸟𞸡𞸢𞸤𞸧𞸩-𞸲𞸴-𞸷𞸹𞸻𞹂𞹇𞹉𞹋𞹍-𞹏𞹑𞹒𞹔𞹗𞹙𞹛𞹝𞹟𞹡𞹢𞹤𞹧-𞹪𞹬-𞹲𞹴-𞹷𞹹-𞹼𞹾𞺀-𞺉𞺋-𞺛𞺡-𞺣𞺥-𞺩𞺫-𞺻𠀀-\U0002a6df𪜀-\U0002b739𫝀-𫠝𫠠-𬺡𬺰-𮯠丽-𪘀𰀀-𱍊\U00031350-\U000323af]|[0-9²³¹¼-¾٠-٩۰-۹߀-߉०-९০-৯৴-৹੦-੯૦-૯୦-୯୲-୷௦-௲౦-౯౸-౾೦-೯൘-൞൦-൸෦-෯๐-๙໐-໙༠-༳၀-၉႐-႙፩-፼ᛮ-ᛰ០-៩៰-៹᠐-᠙᥆-᥏᧐-᧚᪀-᪉᪐-᪙᭐-᭙᮰-᮹᱀-᱉᱐-᱙⁰⁴-⁹₀-₉⅐-ↂↅ-↉①-⒛⓪-⓿❶-➓⳽〇〡-〩〸-〺㆒-㆕㈠-㈩㉈-㉏㉑-㉟㊀-㊉㊱-㊿꘠-꘩ꛦ-ꛯ꠰-꠵꣐-꣙꤀-꤉꧐-꧙꧰-꧹꩐-꩙꯰-꯹０-９𐄇-𐄳𐅀-𐅸𐆊𐆋𐋡-𐋻𐌠-𐌣𐍁𐍊𐏑-𐏕𐒠-𐒩𐡘-𐡟𐡹-𐡿𐢧-𐢯𐣻-𐣿𐤖-𐤛𐦼𐦽𐧀-𐧏𐧒-𐧿𐩀-𐩈𐩽𐩾𐪝-𐪟𐫫-𐫯𐭘-𐭟𐭸-𐭿𐮩-𐮯𐳺-𐳿𐴰-𐴹𐹠-𐹾𐼝-𐼦𐽑-𐽔𐿅-𐿋𑁒-𑁯𑃰-𑃹𑄶-𑄿𑇐-𑇙𑇡-𑇴𑋰-𑋹𑑐-𑑙𑓐-𑓙𑙐-𑙙𑛀-𑛉𑜰-𑜻𑣠-𑣲𑥐-𑥙𑱐-𑱬𑵐-𑵙𑶠-𑶩\U00011f50-\U00011f59𑿀-𑿔𒐀-𒑮𖩠-𖩩\U00016ac0-\U00016ac9𖭐-𖭙𖭛-𖭡𖺀-𖺖\U0001d2c0-\U0001d2d3𝋠-𝋳𝍠-𝍸𝟎-𝟿𞅀-𞅉𞋰-𞋹\U0001e4f0-\U0001e4f9𞣇-𞣏𞥐-𞥙𞱱-𞲫𞲭-𞲯𞲱-𞲴𞴁-𞴭𞴯-𞴽🄀-🄌🯰-🯹]|_)@([a-z](?:_(?!_)|[a-z0-9]){2,30}[a-z0-9]|gif|pic|vid)(?![A-Za-zªµºÀ-ÖØ-öø-ˁˆ-ˑˠ-ˤˬˮͰ-ʹͶͷͺ-ͽͿΆΈ-ΊΌΎ-ΡΣ-ϵϷ-ҁҊ-ԯԱ-Ֆՙՠ-ֈא-תׯ-ײؠ-يٮٯٱ-ۓەۥۦۮۯۺ-ۼۿܐܒ-ܯݍ-ޥޱߊ-ߪߴߵߺࠀ-ࠕࠚࠤࠨࡀ-ࡘࡠ-ࡪ\u0870-\u0887\u0889-\u088eࢠ-\u08c9ऄ-हऽॐक़-ॡॱ-ঀঅ-ঌএঐও-নপ-রলশ-হঽৎড়ঢ়য়-ৡৰৱৼਅ-ਊਏਐਓ-ਨਪ-ਰਲਲ਼ਵਸ਼ਸਹਖ਼-ੜਫ਼ੲ-ੴઅ-ઍએ-ઑઓ-નપ-રલળવ-હઽૐૠૡૹଅ-ଌଏଐଓ-ନପ-ରଲଳଵ-ହଽଡ଼ଢ଼ୟ-ୡୱஃஅ-ஊஎ-ஐஒ-கஙசஜஞடணதந-பம-ஹௐఅ-ఌఎ-ఐఒ-నప-హఽౘ-ౚ\u0c5dౠౡಀಅ-ಌಎ-ಐಒ-ನಪ-ಳವ-ಹಽ\u0cddೞೠೡೱೲഄ-ഌഎ-ഐഒ-ഺഽൎൔ-ൖൟ-ൡൺ-ൿඅ-ඖක-නඳ-රලව-ෆก-ะาำเ-ๆກຂຄຆ-ຊຌ-ຣລວ-ະາຳຽເ-ໄໆໜ-ໟༀཀ-ཇཉ-ཬྈ-ྌက-ဪဿၐ-ၕၚ-ၝၡၥၦၮ-ၰၵ-ႁႎႠ-ჅჇჍა-ჺჼ-ቈቊ-ቍቐ-ቖቘቚ-ቝበ-ኈኊ-ኍነ-ኰኲ-ኵኸ-ኾዀዂ-ዅወ-ዖዘ-ጐጒ-ጕጘ-ፚᎀ-ᎏᎠ-Ᏽᏸ-ᏽᐁ-ᙬᙯ-ᙿᚁ-ᚚᚠ-ᛪᛱ-ᛸᜀ-ᜑ\u171f-ᜱᝀ-ᝑᝠ-ᝬᝮ-ᝰក-ឳៗៜᠠ-ᡸᢀ-ᢄᢇ-ᢨᢪᢰ-ᣵᤀ-ᤞᥐ-ᥭᥰ-ᥴᦀ-ᦫᦰ-ᧉᨀ-ᨖᨠ-ᩔᪧᬅ-ᬳᭅ-\u1b4cᮃ-ᮠᮮᮯᮺ-ᯥᰀ-ᰣᱍ-ᱏᱚ-ᱽᲀ-ᲈᲐ-ᲺᲽ-Ჿᳩ-ᳬᳮ-ᳳᳵᳶᳺᴀ-ᶿḀ-ἕἘ-Ἕἠ-ὅὈ-Ὅὐ-ὗὙὛὝὟ-ώᾀ-ᾴᾶ-ᾼιῂ-ῄῆ-ῌῐ-ΐῖ-Ίῠ-Ῥῲ-ῴῶ-ῼⁱⁿₐ-ₜℂℇℊ-ℓℕℙ-ℝℤΩℨK-ℭℯ-ℹℼ-ℿⅅ-ⅉⅎↃↄⰀ-ⳤⳫ-ⳮⳲⳳⴀ-ⴥⴧⴭⴰ-ⵧⵯⶀ-ⶖⶠ-ⶦⶨ-ⶮⶰ-ⶶⶸ-ⶾⷀ-ⷆⷈ-ⷎⷐ-ⷖⷘ-ⷞⸯ々〆〱-〵〻〼ぁ-ゖゝ-ゟァ-ヺー-ヿㄅ-ㄯㄱ-ㆎㆠ-ㆿㇰ-ㇿ㐀-䶿一-ꒌꓐ-ꓽꔀ-ꘌꘐ-ꘟꘪꘫꙀ-ꙮꙿ-ꚝꚠ-ꛥꜗ-ꜟꜢ-ꞈꞋ-ꟊ\ua7d0\ua7d1\ua7d3\ua7d5-\ua7d9\ua7f2-ꠁꠃ-ꠅꠇ-ꠊꠌ-ꠢꡀ-ꡳꢂ-ꢳꣲ-ꣷꣻꣽꣾꤊ-ꤥꤰ-ꥆꥠ-ꥼꦄ-ꦲꧏꧠ-ꧤꧦ-ꧯꧺ-ꧾꨀ-ꨨꩀ-ꩂꩄ-ꩋꩠ-ꩶꩺꩾ-ꪯꪱꪵꪶꪹ-ꪽꫀꫂꫛ-ꫝꫠ-ꫪꫲ-ꫴꬁ-ꬆꬉ-ꬎꬑ-ꬖꬠ-ꬦꬨ-ꬮꬰ-ꭚꭜ-ꭩꭰ-ꯢ가-힣ힰ-ퟆퟋ-ퟻ豈-舘並-龎ﬀ-ﬆﬓ-ﬗיִײַ-ﬨשׁ-זּטּ-לּמּנּסּףּפּצּ-ﮱﯓ-ﴽﵐ-ﶏﶒ-ﷇﷰ-ﷻﹰ-ﹴﹶ-ﻼＡ-Ｚａ-ｚｦ-ﾾￂ-ￇￊ-ￏￒ-ￗￚ-ￜ𐀀-𐀋𐀍-𐀦𐀨-𐀺𐀼𐀽𐀿-𐁍𐁐-𐁝𐂀-𐃺𐊀-𐊜𐊠-𐋐𐌀-𐌟𐌭-𐍀𐍂-𐍉𐍐-𐍵𐎀-𐎝𐎠-𐏃𐏈-𐏏𐐀-𐒝𐒰-𐓓𐓘-𐓻𐔀-𐔧𐔰-𐕣\U00010570-\U0001057a\U0001057c-\U0001058a\U0001058c-\U00010592\U00010594\U00010595\U00010597-\U000105a1\U000105a3-\U000105b1\U000105b3-\U000105b9\U000105bb\U000105bc𐘀-𐜶𐝀-𐝕𐝠-𐝧\U00010780-\U00010785\U00010787-\U000107b0\U000107b2-\U000107ba𐠀-𐠅𐠈𐠊-𐠵𐠷𐠸𐠼𐠿-𐡕𐡠-𐡶𐢀-𐢞𐣠-𐣲𐣴𐣵𐤀-𐤕𐤠-𐤹𐦀-𐦷𐦾𐦿𐨀𐨐-𐨓𐨕-𐨗𐨙-𐨵𐩠-𐩼𐪀-𐪜𐫀-𐫇𐫉-𐫤𐬀-𐬵𐭀-𐭕𐭠-𐭲𐮀-𐮑𐰀-𐱈𐲀-𐲲𐳀-𐳲𐴀-𐴣𐺀-𐺩𐺰𐺱𐼀-𐼜𐼧𐼰-𐽅\U00010f70-\U00010f81𐾰-𐿄𐿠-𐿶𑀃-𑀷\U00011071\U00011072\U00011075𑂃-𑂯𑃐-𑃨𑄃-𑄦𑅄𑅇𑅐-𑅲𑅶𑆃-𑆲𑇁-𑇄𑇚𑇜𑈀-𑈑𑈓-𑈫\U0001123f\U00011240𑊀-𑊆𑊈𑊊-𑊍𑊏-𑊝𑊟-𑊨𑊰-𑋞𑌅-𑌌𑌏𑌐𑌓-𑌨𑌪-𑌰𑌲𑌳𑌵-𑌹𑌽𑍐𑍝-𑍡𑐀-𑐴𑑇-𑑊𑑟-𑑡𑒀-𑒯𑓄𑓅𑓇𑖀-𑖮𑗘-𑗛𑘀-𑘯𑙄𑚀-𑚪𑚸𑜀-𑜚\U00011740-\U00011746𑠀-𑠫𑢠-𑣟𑣿-𑤆𑤉𑤌-𑤓𑤕𑤖𑤘-𑤯𑤿𑥁𑦠-𑦧𑦪-𑧐𑧡𑧣𑨀𑨋-𑨲𑨺𑩐𑩜-𑪉𑪝\U00011ab0-𑫸𑰀-𑰈𑰊-𑰮𑱀𑱲-𑲏𑴀-𑴆𑴈𑴉𑴋-𑴰𑵆𑵠-𑵥𑵧𑵨𑵪-𑶉𑶘𑻠-𑻲\U00011f02\U00011f04-\U00011f10\U00011f12-\U00011f33𑾰𒀀-𒎙𒒀-𒕃\U00012f90-\U00012ff0𓀀-\U0001342f\U00013441-\U00013446𔐀-𔙆𖠀-𖨸𖩀-𖩞\U00016a70-\U00016abe𖫐-𖫭𖬀-𖬯𖭀-𖭃𖭣-𖭷𖭽-𖮏𖹀-𖹿𖼀-𖽊𖽐𖾓-𖾟𖿠𖿡𖿣𗀀-𘟷𘠀-𘳕𘴀-𘴈\U0001aff0-\U0001aff3\U0001aff5-\U0001affb\U0001affd\U0001affe𛀀-\U0001b122\U0001b132𛅐-𛅒\U0001b155𛅤-𛅧𛅰-𛋻𛰀-𛱪𛱰-𛱼𛲀-𛲈𛲐-𛲙𝐀-𝑔𝑖-𝒜𝒞𝒟𝒢𝒥𝒦𝒩-𝒬𝒮-𝒹𝒻𝒽-𝓃𝓅-𝔅𝔇-𝔊𝔍-𝔔𝔖-𝔜𝔞-𝔹𝔻-𝔾𝕀-𝕄𝕆𝕊-𝕐𝕒-𝚥𝚨-𝛀𝛂-𝛚𝛜-𝛺𝛼-𝜔𝜖-𝜴𝜶-𝝎𝝐-𝝮𝝰-𝞈𝞊-𝞨𝞪-𝟂𝟄-𝟋\U0001df00-\U0001df1e\U0001df25-\U0001df2a\U0001e030-\U0001e06d𞄀-𞄬𞄷-𞄽𞅎\U0001e290-\U0001e2ad𞋀-𞋫\U0001e4d0-\U0001e4eb\U0001e7e0-\U0001e7e6\U0001e7e8-\U0001e7eb\U0001e7ed\U0001e7ee\U0001e7f0-\U0001e7fe𞠀-𞣄𞤀-𞥃𞥋𞸀-𞸃𞸅-𞸟𞸡𞸢𞸤𞸧𞸩-𞸲𞸴-𞸷𞸹𞸻𞹂𞹇𞹉𞹋𞹍-𞹏𞹑𞹒𞹔𞹗𞹙𞹛𞹝𞹟𞹡𞹢𞹤𞹧-𞹪𞹬-𞹲𞹴-𞹷𞹹-𞹼𞹾𞺀-𞺉𞺋-𞺛𞺡-𞺣𞺥-𞺩𞺫-𞺻𠀀-\U0002a6df𪜀-\U0002b739𫝀-𫠝𫠠-𬺡𬺰-𮯠丽-𪘀𰀀-𱍊\U00031350-\U000323af]|[0-9²³¹¼-¾٠-٩۰-۹߀-߉०-९০-৯৴-৹੦-੯૦-૯୦-୯୲-୷௦-௲౦-౯౸-౾೦-೯൘-൞൦-൸෦-෯๐-๙໐-໙༠-༳၀-၉႐-႙፩-፼ᛮ-ᛰ០-៩៰-៹᠐-᠙᥆-᥏᧐-᧚᪀-᪉᪐-᪙᭐-᭙᮰-᮹᱀-᱉᱐-᱙⁰⁴-⁹₀-₉⅐-ↂↅ-↉①-⒛⓪-⓿❶-➓⳽〇〡-〩〸-〺㆒-㆕㈠-㈩㉈-㉏㉑-㉟㊀-㊉㊱-㊿꘠-꘩ꛦ-ꛯ꠰-꠵꣐-꣙꤀-꤉꧐-꧙꧰-꧹꩐-꩙꯰-꯹０-９𐄇-𐄳𐅀-𐅸𐆊𐆋𐋡-𐋻𐌠-𐌣𐍁𐍊𐏑-𐏕𐒠-𐒩𐡘-𐡟𐡹-𐡿𐢧-𐢯𐣻-𐣿𐤖-𐤛𐦼𐦽𐧀-𐧏𐧒-𐧿𐩀-𐩈𐩽𐩾𐪝-𐪟𐫫-𐫯𐭘-𐭟𐭸-𐭿𐮩-𐮯𐳺-𐳿𐴰-𐴹𐹠-𐹾𐼝-𐼦𐽑-𐽔𐿅-𐿋𑁒-𑁯𑃰-𑃹𑄶-𑄿𑇐-𑇙𑇡-𑇴𑋰-𑋹𑑐-𑑙𑓐-𑓙𑙐-𑙙𑛀-𑛉𑜰-𑜻𑣠-𑣲𑥐-𑥙𑱐-𑱬𑵐-𑵙𑶠-𑶩\U00011f50-\U00011f59𑿀-𑿔𒐀-𒑮𖩠-𖩩\U00016ac0-\U00016ac9𖭐-𖭙𖭛-𖭡𖺀-𖺖\U0001d2c0-\U0001d2d3𝋠-𝋳𝍠-𝍸𝟎-𝟿𞅀-𞅉𞋰-𞋹\U0001e4f0-\U0001e4f9𞣇-𞣏𞥐-𞥙𞱱-𞲫𞲭-𞲯𞲱-𞲴𞴁-𞴭𞴯-𞴽🄀-🄌🯰-🯹]|_)', re.I)


@dataclasses.dataclass
class User:
    id: typing.Optional[int]
    usernames: tuple
    deleted: bool

    @property
    def key(self):
        return self.usernames[0].casefold() if self.usernames else self.id


@dataclasses.dataclass
class FullUser:
    user: User
    about: str

    @property
    def points_to(self):
        return [x.group()[1:] for x in USERNAME_REGEX.finditer(self.about)]

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            return getattr(self.user, name)