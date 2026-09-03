import { createProduct } from './actions';

export default function ProductForm({ message }: { message?: string }) {
  return <form className="product-form" action={createProduct}>
    <h2>Create your first product</h2>
    <label>Product name<input name="name" required placeholder="e.g. Oversized Utility Jacket" /></label>
    <label>Product image<input name="image" type="file" accept="image/*" required /></label>
    <button className="primary" type="submit">Save product →</button>
    {message && <p className="form-status">{message}</p>}
  </form>;
}
