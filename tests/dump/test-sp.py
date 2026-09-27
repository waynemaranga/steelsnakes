from sectionproperties.pre.geometry import Geometry
from steelsnakes.EU.sections.beams import UniversalBeam
from steelsnakes.EU.sections.channels import ParallelFlangeChannel

def main() -> None:
    # from sectionproperties.pre.library import i_section
    from sectionproperties.pre.library.steel_sections import i_section, channel_section
    from steelsnakes.EU.sections import UB, PFC

    # -- UB
    # UB_1 = UB("254 x 102x 28") # TODO: ADD STRIP TO SECTION NOT FOUND ERROR
    # UB_1: UniversalBeam = UB("254x102x28")
    # print(UB_1)
    # UB_1plot: Geometry = i_section(d=UB_1.d, b=UB_1.b, t_f=UB_1.tf, t_w=UB_1.tw, r=UB_1.r, n_r=32)
    # UB_1plot.plot_geometry()
    # UB_1_area: float = UB_1plot.calculate_area()
    # print(UB_1.get_properties())
    # print(UB_1_area)
    # print(UB_1.A)

    # -- PFC
    PFC_1: ParallelFlangeChannel = PFC("100x50x10")
    for i in [2048, 4096, 8_192, 16_384, 32_768, 65_536, 131_072, 262_144, 524_288, 1_048_576]:
        print(channel_section(d=PFC_1.d, b=PFC_1.b, t_f=PFC_1.tf, t_w=PFC_1.tw, r=PFC_1.r, n_r=i).calculate_area())
    # PFC_1plot.plot_geometry()
    print(PFC_1.A)
    # print(PFC_1plot.calculate_area())



if __name__ == "__main__":
    main()
    print("🐬")
    