import { brand } from "../config/brand";

export default function BrandLockup({
  variant = "default",
  showProductName = true,
  showCompanyName = true,
}) {
  return (
    <div className={`brand-lockup brand-lockup-${variant}`}>
      <div className="brand-logo-shell">
        <img src={brand.logoSrc} alt={brand.logoAlt} className="brand-logo-img" />
      </div>

      {(showProductName || showCompanyName) && (
        <div className="brand-copy">
         <h>
          {showProductName && <div className="brand-product">{brand.productName}</div>}</h>
        </div>
      )}
    </div>
  );
}