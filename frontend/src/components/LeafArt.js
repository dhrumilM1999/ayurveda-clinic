import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
// Decorative leaf drawing used on the login page and dashboard banner.
export function LeafArt({ className }) {
    return (_jsxs("svg", { className: className, style: { color: '#ffffff' }, viewBox: "0 0 200 200", fill: "none", "aria-hidden": "true", children: [_jsx("path", { d: "M100 190C46 160 30 92 100 10c70 82 54 150 0 180Z", fill: "currentColor" }), _jsx("path", { d: "M100 190V40", stroke: "#000", strokeOpacity: ".35", strokeWidth: "3" }), [60, 85, 110, 135, 160].map((y) => (_jsxs("g", { stroke: "#000", strokeOpacity: ".3", strokeWidth: "2.5", strokeLinecap: "round", children: [_jsx("path", { d: `M100 ${y}c-14-8-24-18-30-30` }), _jsx("path", { d: `M100 ${y}c14-8 24-18 30-30` })] }, y)))] }));
}
