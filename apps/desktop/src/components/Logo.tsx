import mark from "../assets/mark.svg?raw";

/**
 * The app mark, inlined so the SVG can inherit the surrounding text colour.
 * Rendering the file as an <img> would freeze currentColor, which the mark
 * relies on to sit on both the accent chip and the boot screen.
 */
export function Logo({ size = 18 }: { size?: number }) {
  return (
    <span className="logo" style={{ width: size, height: size }} dangerouslySetInnerHTML={{ __html: mark }} />
  );
}
