export type IconName = 'home' | 'plus' | 'folder' | 'compass' | 'settings' | 'menu' | 'details' | 'arrow' | 'sparkle' | 'workspace' | 'shield' | 'user';

export default function StudioIcon({ name }: { name: IconName }) {
  const paths = {
    home: <><path d="M2.75 11.35 12 3.5l9.25 7.85"/><path d="M5.25 9.3v9.95a1.25 1.25 0 0 0 1.25 1.25h11a1.25 1.25 0 0 0 1.25-1.25V9.3M9.6 20.5v-4.7a2.4 2.4 0 0 1 4.8 0v4.7"/></>,
    plus: <><rect x="3.5" y="3.5" width="17" height="17" rx="4.75"/><path d="M12 8.5v7M8.5 12h7"/></>,
    folder: <><path d="M5.5 7.5V6a1.5 1.5 0 0 1 1.5-1.5h4l2 2h4a1.5 1.5 0 0 1 1.5 1.5v2"/><path d="M4 9a1.5 1.5 0 0 1 1.5-1.5H9l2 2h7.5A1.5 1.5 0 0 1 20 11v6.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5Z"/></>,
    compass: <><circle cx="12" cy="12" r="8.6"/><path d="m15.55 8.45-2.2 4.9-4.9 2.2 2.2-4.9Z"/></>,
    settings: <><path d="m9.5 4 .7-2h3.6l.7 2 2.1 1.2 2.1-.4 1.8 3.1-1.4 1.6v2.5l1.4 1.6-1.8 3.1-2.1-.4-2.1 1.2-.7 2h-3.6l-.7-2-2.1-1.2-2.1.4L3.5 14l1.4-1.6V9.9L3.5 8.3l1.8-3.1 2.1.4Z" transform="translate(0 1)"/><circle cx="12" cy="12" r="3"/></>,
    menu: <path d="M4 6h16M4 12h16M4 18h16"/>,
    details: <><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></>,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6"/>,
    sparkle: <path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z"/>,
    workspace: <><rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 9h17M9 9v10.5"/></>,
    shield: <><path d="m12 3 8 3v5c0 5-4 8-8 10-4-2-8-5-8-10V6Z"/><path d="m8 12 3 3 5-6"/></>,
    user: <><circle cx="12" cy="8" r="3.5"/><path d="M5 20v-1a7 7 0 0 1 14 0v1"/></>,
  };
  return <svg className="sh-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
