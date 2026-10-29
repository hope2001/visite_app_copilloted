import { useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { useCurrentUser, useAuth } from '../auth/AuthContext';
import { NAV_ITEMS, ROLE_LABELS, hasRole } from '../auth/roles';

function initialsOf(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? '';
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? '') : '';
  return (first + last).toUpperCase();
}

export function Layout() {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const items = NAV_ITEMS.filter((item) => hasRole(user.role, item.roles));
  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__inner">
          <Link to="/" className="brand" onClick={closeMenu}>
            <span className="brand__mark" aria-hidden="true">
              VM
            </span>
            <span className="brand__text">
              <span className="brand__name">Visitor Management</span>
              <span className="brand__tagline">Front desk &amp; access</span>
            </span>
          </Link>

          <button
            type="button"
            className="menu-toggle"
            aria-expanded={menuOpen}
            aria-controls="app-navigation"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="menu-toggle__bar" />
            <span className="menu-toggle__bar" />
            <span className="menu-toggle__bar" />
          </button>

          <div id="app-navigation" className={`app-nav${menuOpen ? ' app-nav--open' : ''}`}>
            <nav aria-label="Main" className="nav-links">
              {items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className="nav-link"
                  onClick={closeMenu}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="user-menu">
              <span className="avatar" aria-hidden="true">
                {initialsOf(user.full_name)}
              </span>
              <span className="user-menu__identity">
                <span className="user-menu__name">{user.full_name}</span>
                <span className="user-menu__role">{ROLE_LABELS[user.role]}</span>
              </span>
              <button type="button" className="sign-out" onClick={logout}>
                Sign out
              </button>
            </div>
          </div>
        </div>
      </header>
      <main className="page">
        <Outlet />
      </main>
    </div>
  );
}
