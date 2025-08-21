// src/theme.js
import { createTheme } from "@mui/material/styles";
import { red } from "@mui/material/colors";
import LinkBehavior from "./components/common/LinkBehaviour";

// Size Options
export const TSizeOptions = {
    sm: "sm",
    md: "md",
    lg: "lg"
};

// Enums converted to objects
export const Spacing = {
    none: 0,
    Small: 0.5,
    Default: 1,
    Medium: 2,
    Large: 3,
    XLarge: 4,
    XXLarge: 5,
    XXXLarge: 7,
};

export const BorderRadius = {
    none: 0,
    Tiny: 0.5,
    Small: 1,
    Default: 2,
    Medium: 4,
    Large: 6,
    XLarge: 8,
    Rounded: 24,
};

export const ControlHeight = {
    Small: 36,
    Default: 40,
    Large: 48,
};

export const FontSize = {
    XSmall: 10,
    Small: 12,
    Default: 14,
    Medium: 16,
    Large: 18,
    XLarge: 20,
    XXLarge: 24,
    XXXLarge: 36,
    Hero: 42,
    AvatarHeader: 32,
    ContentTitle: 17,
    ContentSubtitle: 15,
};

export const FontWeight = {
    Light: 300,
    Normal: 400,
    Medium: 500,
    SemiBold: 600,
    Bold: 700,
    ExtraBold: 800,
};

export const FontFamily = {
    Primary: "Inter, sans-serif",
    Secondary: "Roboto, sans-serif",
};

export const BoxShadow = {
    none: "none",
    Default: "0px 0px 4px rgba(0, 0, 0, 0.1)",
    Medium: "0px 0px 8px rgba(0, 0, 0, 0.2)",
    Large: "0px 0px 16px rgba(0, 0, 0, 0.3)",
};

export const Opacity = {
    Default: 1,
    SemiTransparent: 0.8,
    Transparent: 0.5,
};

export const ZIndex = {
    Button: 10,
    Dropdown: 20,
    Sidebar: 90,
    Header: 1000,
    Modal: 2000,
    Snackbar: 2500,
};

export const LineHeight = {
    Small: "14px",
    Medium: "19px",
    Large: "21px",
    XLarge: "29px",
    XXLarge: "51px",
};

export const CustomColors = {
    // Primary Palette
    MidnightBlue: "#1B3360",
    DeepSkyBlue: "#00AED8",
    AliceBlue: "#F3FBFD",
    LightGrey: "#CDD6DF",
    GhostWhite: "#F5F7FD",
    // Secondary Palette
    MidnightBlueA75: "#4D5F81",
    DeepSkyBlueA40: "#89CEDF",
    AliceBlueA65: "#EEF3F4",
    LighterGreyA20: "#E0E2E4",
    While: "#ffffff",
    // Typography - grey colours
    Downriver: "#162D59",
    DownriverGrey: "#0A1F44",
    PortGore: "#4E5D78",
    RegentGray: "#8A94A6",
    CadetBlue: "#B0B7C3",
    // Typography - neutral colours
    Ghost: "#C1C7D0",
    AthensGrey: "#EBECF0",
    Casper: "#FAFBFC",
    // Icons Palette - icon colours
    Pumpkin: "#FD7E14",
    Meadow: "#12B886",
    SlateBlue: "#6745DB",
    Cobalt: "#104BA2",
    Bismark: "#556E7D",
    // Icons Palette - squares (background colours)
    PatternsBlue: "#D0EBFF",
    DarkPatternsBlue: "#00ACD6",
    BlanchedAlmond: "#FFE8CC",
    Hummingbird: "#C3FAE8",
    Lavender: "#E8E2FF",
    Purple: "#6745DB",
    Solitude: "#E3EDFF",
    PaleBlue: "#D8E2E9",
    Peach: "#FFD7D8",
    White: "#fff",
    Black: "#0F172A",
    CornflowerBlue: "#264887",

    // Other UI colors
    UIGrey100: "#F8FAFC",
    UIGrey200: "#F1F5F9",
    UIGrey300: "#E2E8F0",
    UIGrey400: "#CBD5E1",
    UIGrey500: "#94A3B8",
    UIGrey600: "#64748B",
    UIGrey800: "#334155",
    UIGrey900: "#1E293B",
    SecretGarden: "#54B489",
    DarkRed: "#C1333A",
    Red: red.A400,
    LightRed: "#F07272",
    SecondaryLight: "#D8E2F1",
};

export const theme = createTheme({
    palette: {
        primary: {
            main: CustomColors.DeepSkyBlue,
            contrastText: CustomColors.White,
        },
        secondary: {
            main: CustomColors.MidnightBlue,
            dark: CustomColors.UIGrey800,
            contrastText: CustomColors.UIGrey200,
        },
        default: {
            main: CustomColors.White,
            contrastText: CustomColors.UIGrey800,
        },
        background: {
            default: CustomColors.White,
            paper: CustomColors.White,
        },
        backgroundSecondary: {
            default: CustomColors.MidnightBlue,
        },
        backgroundGrey: {
            default: CustomColors.UIGrey100,
        },
        text: {
            primary: CustomColors.UIGrey900,
            secondary: CustomColors.UIGrey500,
            secondaryDarker: CustomColors.UIGrey600,
        },
        border: {
            main: CustomColors.UIGrey400,
            light: CustomColors.SecondaryLight,
            dark: CustomColors.UIGrey500,
        },
        info: {
            main: CustomColors.DeepSkyBlue,
            contrastText: CustomColors.White,
        },
        success: {
            main: CustomColors.SecretGarden,
            contrastText: CustomColors.White,
        },
        error: {
            main: red.A400,
        },
        disabled: {
            main: CustomColors.UIGrey200,
        },
    },
    typography: {
        fontFamily: FontFamily.Primary,

        h1: {
            fontFamily: FontFamily.Primary,
            fontSize: FontSize.Hero,
            fontWeight: FontWeight.Bold,
            lineHeight: LineHeight.XXLarge,
        },
        h2: {
            fontFamily: FontFamily.Primary,
            fontSize: FontSize.XXXLarge,
            fontWeight: FontWeight.Bold,
        },
        h3: {
            fontFamily: FontFamily.Primary,
            fontSize: FontSize.XXLarge,
            fontWeight: FontWeight.Bold,
            lineHeight: LineHeight.XLarge,
        },
        h4: {
            fontFamily: FontFamily.Primary,
            fontSize: FontSize.ContentTitle,
            fontWeight: FontWeight.SemiBold,
            lineHeight: LineHeight.Large,
        },
        h5: {
            fontFamily: FontFamily.Primary,
            fontSize: FontSize.ContentSubtitle,
            fontWeight: FontWeight.Medium,
            lineHeight: LineHeight.Medium,
        },
        h6: {
            fontFamily: FontFamily.Primary,
            fontSize: FontSize.Default,
            fontWeight: FontWeight.Medium,
        },
        h7: {
            fontFamily: FontFamily.Primary,
            fontWeight: FontWeight.Medium,
            fontSize: FontSize.XSmall,
            lineHeight: LineHeight.Small,
            color: CustomColors.UIGrey600,
        },
        subtitle1: {},
        subtitle2: {
            color: CustomColors.RegentGray,
        },
        body1: {
            fontSize: FontSize.Default,
            fontWeight: FontWeight.Normal,
            lineHeight: LineHeight.Medium,
        },
        body2: { fontSize: FontSize.Small, lineHeight: LineHeight.Medium },

        body: {
            fontSize: FontSize.Default,
            fontWeight: FontWeight.Normal,
            lineHeight: LineHeight.Medium,
            color: CustomColors.UIGrey900,
        },
        bodySmall: {
            fontSize: FontSize.Small,
            fontWeight: FontWeight.Normal,
            lineHeight: LineHeight.Medium,
            color: CustomColors.UIGrey600,
        },
        bodyXSmall: {
            fontSize: FontSize.XSmall,
            fontWeight: FontWeight.Normal,
            lineHeight: LineHeight.Small,
            color: CustomColors.UIGrey800,
        },
        bodyLarge: {
            fontSize: FontSize.Large,
        },
        bodyXLarge: {
            fontSize: FontSize.XLarge,
        },
        caption: {},
        caption2: {
            fontSize: FontSize.Default,
            color: CustomColors.PortGore,
        },
        button: {},
        overline: {},
    },
    components: {
        MuiChip: {
            styleOverrides: {
                root: {
                    borderRadius: BorderRadius.Medium,
                },
            },
        },
        MuiLink: {
            defaultProps: {
                component: LinkBehavior,
                underline: "none",
            },
        },
        MuiBreadcrumbs: {
            styleOverrides: {
                root: ({ theme: _theme }) => ({
                    marginBottom: _theme.spacing(Spacing.Large),
                    lineHeight: 1.5714, // 22px of default font size 14px
                }),
            },
        },
        MuiPaper: {
            styleOverrides: {
                elevation1: {
                    border: `1px solid ${CustomColors.LighterGreyA20}`,
                    boxShadow: BoxShadow.none,
                },
            },
        },
        MuiAlert: {
            styleOverrides: {
                root: {
                    borderRadius: BorderRadius.XLarge,
                },
                message: {
                    color: CustomColors.DownriverGrey,
                },
                standardInfo: {
                    background: CustomColors.PatternsBlue,
                },
                standardWarning: {
                    background: CustomColors.BlanchedAlmond,
                },
            },
        },
        MuiButtonBase: {},
        MuiButton: {
            styleOverrides: {
                root: {
                    minHeight: ControlHeight.Default,
                    borderRadius: BorderRadius.Rounded,
                    lineHeight: "normal",
                    textTransform: "none",
                },
                containedPrimary: {
                    fontWeight: FontWeight.Medium,
                },
            },
        },
        MuiTableRow: {
            styleOverrides: {
                root: {
                    "&.MuiTableRow-hover": {
                        "&:hover": {
                            backgroundColor: CustomColors.AthensGrey,
                        },
                    },
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    border: `1px solid ${CustomColors.LighterGreyA20}`,
                },
            },
        },
        MuiCardContent: {
            styleOverrides: {
                root: {
                    padding: 24,
                },
            },
        },
        MuiFormHelperText: {
            styleOverrides: {
                root: {
                    fontSize: FontSize.Small,
                    fontWeight: FontWeight.Normal,
                    lineHeight: LineHeight.Medium,
                    color: CustomColors.UIGrey800,

                    "&.Mui-error": {
                        color: "#ff1744",
                    },
                },
            },
        },
        MuiDialogContentText: {
            styleOverrides: {
                root: {
                    color: CustomColors.UIGrey800,
                },
            },
        },
        MuiTab: {
            styleOverrides: {
                root: {
                    textTransform: "none",
                    color: "grey",
                    fontWeight: FontWeight.SemiBold,
                },
            },
        },
    },
    zIndex: {
        snackbar: ZIndex.Snackbar,
    },
});

export const getMarginSize = (marginSize) => {
    switch (marginSize) {
        case TSizeOptions.sm:
            return Spacing.Default;
        case TSizeOptions.md:
            return Spacing.Medium;
        case TSizeOptions.lg:
            return Spacing.Large;
        default:
            return Spacing.Default;
    }
};